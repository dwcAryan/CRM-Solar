import csv
import io
import itertools
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from masters.models import LeadSource

from .models import ImportBatch, Lead
from .utils import find_duplicate_lead

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 5000


def sanitize_csv_cell(value: Any) -> str:
    """
    Prevents CSV / Formula injection attacks by prepending an apostrophe (')
    if the cell value starts with '=', '+', '-', or '@'.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if s and s[0] in ('=', '+', '-', '@'):
        return f"'{s}"
    return s


def normalize_indian_phone(raw_phone: Any) -> Optional[str]:
    """
    Normalizes Indian phone numbers:
    - Strips whitespace, dashes, plus signs, dots, parens.
    - Strips '91' prefix for 12-digit numbers.
    - Strips leading '0' for 11-digit numbers.
    Returns 10-digit phone string if valid, else None.
    """
    if not raw_phone:
        return None
    cleaned = re.sub(r'\D', '', str(raw_phone))
    if len(cleaned) == 12 and cleaned.startswith('91'):
        cleaned = cleaned[2:]
    elif len(cleaned) == 11 and cleaned.startswith('0'):
        cleaned = cleaned[1:]
    if len(cleaned) == 10 and cleaned.isdigit():
        return cleaned
    return None


COLUMN_SYNONYMS = {
    'name': ['name', 'full name', 'customer name', 'client name', 'lead name', 'contact name'],
    'phone': ['phone', 'mobile', 'contact', 'phone number', 'mobile number', 'cell', 'contact number'],
    'alt_phone': ['alt phone', 'alternate phone', 'alt mobile', 'secondary phone', 'other phone'],
    'email': ['email', 'email address', 'mail'],
    'city': ['city', 'town', 'district', 'location'],
    'address': ['address', 'street', 'residence', 'location address'],
    'pincode': ['pincode', 'pin code', 'zip', 'zipcode', 'postal code'],
    'source': ['source', 'lead source', 'channel', 'campaign'],
    'monthly_bill': ['monthly bill', 'bill', 'electricity bill', 'power bill', 'avg bill', 'average bill'],
    'roof_type': ['roof type', 'roof', 'roofing'],
    'property_type': ['property type', 'property', 'building type'],
    'owner_or_tenant': ['owner or tenant', 'occupancy', 'owner/tenant', 'ownership'],
    'remark': ['remark', 'remarks', 'note', 'notes', 'comment', 'comments'],
}


def auto_match_headers(headers: List[str]) -> Dict[str, str]:
    """
    Given a list of column headers from the file, returns a dictionary
    mapping CRM field name -> matched file header.
    """
    matched: Dict[str, str] = {}
    normalized_headers = {h.strip().lower(): h for h in headers if h}

    for crm_field, synonyms in COLUMN_SYNONYMS.items():
        for syn in synonyms:
            if syn in normalized_headers:
                matched[crm_field] = normalized_headers[syn]
                break

    return matched


def parse_file_rows(uploaded_file) -> Tuple[List[str], List[List[str]]]:
    """
    Validates and extracts headers and data rows from a .csv or .xlsx file.
    Uses utf-8-sig encoding for CSVs to correctly handle Excel-saved BOMs.
    """
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError(f"File size exceeds maximum allowed limit of 5 MB ({uploaded_file.size / (1024 * 1024):.2f} MB).")

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ('.csv', '.xlsx'):
        raise ValidationError(f"Invalid file type '{ext}'. Only .csv and .xlsx files are supported.")

    rows: List[List[str]] = []

    if ext == '.csv':
        content = uploaded_file.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except Exception as e:
                raise ValidationError(f"Unable to decode CSV file: {e}")

        reader = csv.reader(io.StringIO(text))
        for r in reader:
            if any(cell.strip() for cell in r if cell):
                rows.append([cell.strip() for cell in r])

    elif ext == '.xlsx':
        try:
            import openpyxl
            wb = openpyxl.load_workbook(uploaded_file, data_only=True)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                r_str = [str(c).strip() if c is not None else "" for c in row]
                if any(r_str):
                    rows.append(r_str)
        except Exception as e:
            raise ValidationError(f"Unable to parse Excel file: {e}")

    if not rows:
        raise ValidationError("The uploaded file contains no data rows.")

    headers = rows[0]
    data_rows = rows[1:]

    if len(data_rows) > MAX_ROWS:
        raise ValidationError(f"File contains {len(data_rows)} rows, which exceeds the maximum limit of {MAX_ROWS} rows.")

    return headers, data_rows


def execute_csv_import(
    uploaded_file,
    mapping: Dict[str, str],
    duplicate_action: str = 'skip',
    assignment_mode: str = 'unassigned',
    single_user_id: Optional[int] = None,
    round_robin_user_ids: Optional[List[int]] = None,
    user: Optional[User] = None,
) -> Tuple[ImportBatch, Dict[str, Any]]:
    """
    Executes row-by-row validation and import inside an atomic transaction.
    """
    headers, data_rows = parse_file_rows(uploaded_file)
    header_to_idx = {h: idx for idx, h in enumerate(headers)}

    def get_val(row: List[str], crm_field: str) -> str:
        col_name = mapping.get(crm_field)
        if col_name and col_name in header_to_idx:
            idx = header_to_idx[col_name]
            if idx < len(row):
                return row[idx].strip()
        return ""

    # Pre-fetch or prepare sources
    sources_by_name = {s.name.lower(): s for s in LeadSource.objects.filter(is_active=True)}
    other_source, _ = LeadSource.objects.get_or_create(name='Other', defaults={'is_active': True})

    # Prepare assignment cycle
    rr_users: List[User] = []
    if assignment_mode == 'round_robin' and round_robin_user_ids:
        rr_users = list(User.objects.filter(id__in=round_robin_user_ids, is_active=True))
    rr_cycle = itertools.cycle(rr_users) if rr_users else None

    single_user: Optional[User] = None
    if assignment_mode == 'single' and single_user_id:
        single_user = User.objects.filter(id=single_user_id, is_active=True).first()

    total_rows = len(data_rows)
    imported_count = 0
    skipped_count = 0
    duplicate_count = 0
    failed_count = 0
    failed_rows: List[Dict[str, Any]] = []

    seen_phones_in_file: Dict[str, int] = {}
    leads_to_create: List[Lead] = []

    # Run in transaction
    with transaction.atomic():
        batch = ImportBatch.objects.create(
            file_name=uploaded_file.name,
            imported_by=user if user and user.is_authenticated else None,
            total_rows=total_rows,
        )

        for row_idx, row in enumerate(data_rows, start=2):  # Row 1 is header
            name = get_val(row, 'name')
            raw_phone = get_val(row, 'phone')
            alt_phone = get_val(row, 'alt_phone')
            email = get_val(row, 'email')
            city = get_val(row, 'city') or 'Ahmedabad'
            address = get_val(row, 'address')
            pincode = get_val(row, 'pincode')
            source_text = get_val(row, 'source')
            monthly_bill_str = get_val(row, 'monthly_bill')
            roof_type = get_val(row, 'roof_type') or 'RCC flat'
            property_type = get_val(row, 'property_type') or 'residential'
            owner_or_tenant = get_val(row, 'owner_or_tenant') or 'owner'
            remark = get_val(row, 'remark')

            # 1. Validation: name required
            if not name:
                failed_count += 1
                failed_rows.append({
                    'row': row_idx,
                    'name': name,
                    'phone': raw_phone,
                    'error': 'Customer Name is required.',
                })
                continue

            # 2. Validation: phone required and normalized to 10 digits
            norm_phone = normalize_indian_phone(raw_phone)
            if not norm_phone:
                failed_count += 1
                failed_rows.append({
                    'row': row_idx,
                    'name': name,
                    'phone': raw_phone,
                    'error': f"Invalid Indian phone number '{raw_phone}'. Must normalize to 10 digits.",
                })
                continue

            # 3. Validation: email if provided
            if email:
                try:
                    validate_email(email)
                except ValidationError:
                    failed_count += 1
                    failed_rows.append({
                        'row': row_idx,
                        'name': name,
                        'phone': raw_phone,
                        'error': f"Invalid email format '{email}'.",
                    })
                    continue

            # 4. Monthly bill parsing if provided
            monthly_bill: Optional[Decimal] = None
            if monthly_bill_str:
                clean_bill = re.sub(r'[^\d\.]', '', monthly_bill_str)
                if clean_bill:
                    try:
                        monthly_bill = Decimal(clean_bill)
                    except InvalidOperation:
                        pass

            # 5. Duplicate Detection: inside file & database
            is_dup_in_file = norm_phone in seen_phones_in_file
            existing_lead = find_duplicate_lead(norm_phone)

            if is_dup_in_file or existing_lead:
                duplicate_count += 1

                if duplicate_action == 'skip':
                    skipped_count += 1
                    continue
                elif duplicate_action == 'update_empty':
                    if existing_lead:
                        updated_fields = []
                        if not existing_lead.email and email:
                            existing_lead.email = email
                            updated_fields.append('email')
                        if not existing_lead.city and city:
                            existing_lead.city = city
                            updated_fields.append('city')
                        if not existing_lead.address and address:
                            existing_lead.address = address
                            updated_fields.append('address')
                        if not existing_lead.monthly_bill and monthly_bill:
                            existing_lead.monthly_bill = monthly_bill
                            updated_fields.append('monthly_bill')
                        if not existing_lead.roof_type and roof_type:
                            existing_lead.roof_type = roof_type
                            updated_fields.append('roof_type')
                        if not existing_lead.property_type and property_type:
                            existing_lead.property_type = property_type
                            updated_fields.append('property_type')
                        if not existing_lead.remark and remark:
                            existing_lead.remark = remark[:500]
                            updated_fields.append('remark')
                        if updated_fields:
                            existing_lead.save()
                    skipped_count += 1
                    continue
                elif duplicate_action == 'create_anyway':
                    # Fall through to create duplicate lead
                    pass

            # 6. Source mapping
            source_obj = other_source
            if source_text:
                matched_source = sources_by_name.get(source_text.lower())
                if matched_source:
                    source_obj = matched_source
                else:
                    # Create or map to Other
                    source_obj = other_source

            # 7. Assignment
            assigned_user: Optional[User] = None
            if assignment_mode == 'single' and single_user:
                assigned_user = single_user
            elif assignment_mode == 'round_robin' and rr_cycle:
                assigned_user = next(rr_cycle)

            # 8. Follow-up rule: status New + follow-up today
            new_lead = Lead(
                name=name[:150],
                phone=norm_phone,
                alt_phone=alt_phone[:20] if alt_phone else '',
                email=email,
                address=address,
                city=city[:100],
                pincode=pincode[:20],
                source=source_obj,
                property_type=property_type[:50],
                monthly_bill=monthly_bill,
                roof_type=roof_type[:50],
                owner_or_tenant=owner_or_tenant[:50],
                assigned_to=assigned_user,
                status=Lead.Status.NEW,
                next_action='First call attempt',
                next_followup_at=timezone.now(),  # Core rule: scheduled for today
                import_batch=batch,
                remark=remark[:500] if remark else '',
            )
            leads_to_create.append(new_lead)
            seen_phones_in_file[norm_phone] = row_idx
            imported_count += 1

        if leads_to_create:
            Lead.objects.bulk_create(leads_to_create)

        batch.imported_count = imported_count
        batch.skipped_count = skipped_count
        batch.duplicate_count = duplicate_count
        batch.failed_count = failed_count
        batch.failed_rows_json = failed_rows
        batch.save()

    results = {
        'batch_id': batch.id,
        'total_rows': total_rows,
        'imported_count': imported_count,
        'skipped_count': skipped_count,
        'duplicate_count': duplicate_count,
        'failed_count': failed_count,
        'errors': failed_rows,
    }

    return batch, results


def generate_failed_rows_csv(failed_rows: List[Dict[str, Any]]) -> str:
    """
    Generates a CSV string of failed rows with formula injection protection.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Row', 'Name', 'Phone', 'Error'])
    for item in failed_rows:
        writer.writerow([
            sanitize_csv_cell(item.get('row', '')),
            sanitize_csv_cell(item.get('name', '')),
            sanitize_csv_cell(item.get('phone', '')),
            sanitize_csv_cell(item.get('error', '')),
        ])
    return output.getvalue()


def undo_import_batch(batch_id: int, user: Optional[User] = None) -> Tuple[bool, str, int]:
    """
    Undoes a whole import batch in a transaction:
    Deletes all leads created under this batch and marks batch as reverted.
    """
    with transaction.atomic():
        try:
            batch = ImportBatch.objects.select_for_update().get(id=batch_id)
        except ImportBatch.DoesNotExist:
            return False, "Import batch not found.", 0

        if batch.is_reverted:
            return False, "This import batch has already been undone / reverted.", 0

        leads_to_delete = Lead.objects.filter(import_batch=batch)
        deleted_count = leads_to_delete.count()
        leads_to_delete.delete()

        batch.is_reverted = True
        batch.reverted_at = timezone.now()
        batch.reverted_by = user if user and user.is_authenticated else None
        batch.save()

    return True, f"Successfully undone batch #{batch_id}. Deleted {deleted_count} imported leads.", deleted_count
