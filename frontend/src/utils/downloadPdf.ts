import { notifications } from '@mantine/notifications';
import { apiClient } from '../api/client';

/**
 * Universal secure PDF download helper (Phase 14M).
 * - Sends authorization header via apiClient
 * - Displays loading notification with spinner
 * - Extracts filename from Content-Disposition header (RFC 5987 aware)
 * - Safe on iOS Safari and mobile Chrome without popup-blocker triggers
 * - Catches 401/403/500 errors and surfaces friendly error toasts
 */
export async function downloadPdfBlob(
  url: string,
  defaultFilename: string = 'document.pdf'
): Promise<void> {
  const notifId = `pdf-download-${Date.now()}`;

  notifications.show({
    id: notifId,
    loading: true,
    title: 'Generating PDF',
    message: 'Preparing document download...',
    autoClose: false,
    withCloseButton: false,
  });

  try {
    const res = await apiClient.get(url, {
      responseType: 'blob',
    });

    let filename = defaultFilename;
    const disposition = res.headers['content-disposition'];
    if (disposition) {
      // RFC 5987 filename* takes precedence over filename
      const rfc5987Match = disposition.match(/filename\*=UTF-8''([^;\r\n"']+)/i);
      if (rfc5987Match && rfc5987Match[1]) {
        try {
          filename = decodeURIComponent(rfc5987Match[1]);
        } catch {
          filename = rfc5987Match[1];
        }
      } else {
        const stdMatch = disposition.match(/filename=['"]?([^;\r\n"']+)['"]?/i);
        if (stdMatch && stdMatch[1]) {
          filename = stdMatch[1];
        }
      }
    }

    const blob = new Blob([res.data], { type: 'application/pdf' });
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Clean up blob URL after delay to support mobile browsers
    setTimeout(() => {
      window.URL.revokeObjectURL(downloadUrl);
    }, 1000);

    notifications.update({
      id: notifId,
      color: 'teal',
      title: 'Download Complete',
      message: `${filename} downloaded successfully.`,
      loading: false,
      autoClose: 3000,
    });
  } catch (err: any) {
    let errorMessage = 'Failed to generate PDF. Please try again.';
    const status = err?.response?.status;

    if (status === 401) {
      errorMessage = 'Session expired. Please sign in again.';
    } else if (status === 403) {
      errorMessage = 'Access denied. You do not have permission to download this PDF.';
    } else if (status === 404) {
      errorMessage = 'Document or quote record not found.';
    } else if (status === 500) {
      errorMessage = 'Server error during PDF generation. Please contact support.';
    }

    notifications.update({
      id: notifId,
      color: 'red',
      title: 'Download Failed',
      message: errorMessage,
      loading: false,
      autoClose: 5000,
    });
    throw err;
  }
}
