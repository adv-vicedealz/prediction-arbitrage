/**
 * Format market slug to readable name
 * e.g., "btc-updown-15m-1768095000" -> "BTC @ 14:30"
 */
export function formatMarketName(slug: string): string {
  if (!slug) return '';

  const parts = slug.split('-');
  const timestamp = parseInt(parts[parts.length - 1]);

  // Get asset type (BTC/ETH)
  const asset = slug.toLowerCase().includes('btc') ? 'BTC' :
                slug.toLowerCase().includes('eth') ? 'ETH' : '???';

  // Convert timestamp to time (ET)
  if (!isNaN(timestamp) && timestamp > 1000000000) {
    const date = new Date(timestamp * 1000);
    const time = date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'America/New_York'
    });
    return `${asset} @ ${time} ET`;
  }

  return slug;
}

/**
 * Format market slug with full details
 * e.g., "btc-updown-15m-1768095000" -> "BTC 15min @ 14:30 - 14:45"
 */
export function formatMarketNameFull(slug: string): string {
  if (!slug) return '';

  const parts = slug.split('-');
  const timestamp = parseInt(parts[parts.length - 1]);

  // Get asset type (BTC/ETH)
  const asset = slug.toLowerCase().includes('btc') ? 'BTC' :
                slug.toLowerCase().includes('eth') ? 'ETH' : '???';

  // Convert timestamp to time range (ET)
  if (!isNaN(timestamp) && timestamp > 1000000000) {
    const startDate = new Date(timestamp * 1000);
    const endDate = new Date((timestamp + 15 * 60) * 1000);

    const formatTime = (d: Date) => d.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'America/New_York'
    });

    return `${asset} 15min @ ${formatTime(startDate)} - ${formatTime(endDate)} ET`;
  }

  return slug;
}

/**
 * Get just the time from a market slug
 * e.g., "btc-updown-15m-1768095000" -> "14:30"
 */
export function getMarketTime(slug: string): string {
  if (!slug) return '';

  const parts = slug.split('-');
  const timestamp = parseInt(parts[parts.length - 1]);

  if (!isNaN(timestamp) && timestamp > 1000000000) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'America/New_York'
    });
  }

  return '';
}

/**
 * Get asset type from slug (BTC/ETH)
 */
export function getAssetType(slug: string): string {
  if (!slug) return '???';
  return slug.toLowerCase().includes('btc') ? 'BTC' :
         slug.toLowerCase().includes('eth') ? 'ETH' : '???';
}
