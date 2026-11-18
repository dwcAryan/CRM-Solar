import factory
from django.utils import timezone

from accounts.models import User
from activities.models import Activity
from leads.models import Lead
from masters.models import Region
from quotes.models import Quote
from surveys.models import Survey


class RegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Region
        django_get_or_create = ('code',)

    code = 'IN'
    name = 'India'
    currency = 'INR'
    currency_symbol = '₹'
    phone_country_code = '+91'
    default_timezone = 'Asia/Kolkata'


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = "Test"
    last_name = factory.Sequence(lambda n: f"User{n}")
    role = User.Role.SALESPERSON
    is_active = True

    @factory.post_generation
    def allowed_regions(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for region in extracted:
                self.allowed_regions.add(region)
        else:
            region, _ = Region.objects.get_or_create(code='IN', defaults={'name': 'India', 'currency': 'INR', 'phone_country_code': '+91', 'default_timezone': 'Asia/Kolkata'})
            self.allowed_regions.add(region)


class LeadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lead

    name = factory.Sequence(lambda n: f"Lead Customer {n}")
    phone = factory.Sequence(lambda n: f"+9198250{n:05d}")
    status = Lead.Status.NEW
    region = factory.SubFactory(RegionFactory)
    assigned_to = factory.SubFactory(UserFactory, role=User.Role.SALESPERSON)


class SurveyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Survey

    lead = factory.SubFactory(LeadFactory)
    scheduled_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=1))
    status = Survey.Status.BOOKED


class QuoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Quote

    lead = factory.SubFactory(LeadFactory)
    version = 1
    system_size_kw = 5.0
    brand = "Waaree 540W Mono PERC"
    price = 250000.00
    status = Quote.Status.DRAFT


class ActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Activity

    lead = factory.SubFactory(LeadFactory)
    type = Activity.Type.CALL
    notes = "Initial follow-up call"
