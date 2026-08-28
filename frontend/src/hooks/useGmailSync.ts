/**
 * Re-export useSync as useGmailSync for backward compatibility.
 * Global background sync is now provided through SyncContext.
 */
export { useSync as useGmailSync, useSync } from '../context/SyncContext';
