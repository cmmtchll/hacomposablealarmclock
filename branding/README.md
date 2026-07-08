# Branding Assets

This folder contains source branding assets for the integration.

- `icon.svg`: square mark intended for integration icon usage.
- `logo.svg`: wider wordmark intended for documentation and release notes.

## Home Assistant Brands Submission

Home Assistant integration branding is served from the separate `home-assistant/brands` repository.

To publish branding:

1. Export `icon.svg` to `icon.png` (256x256, transparent background recommended).
2. Export `logo.svg` (or a simplified variant) to `logo.png` (256x256).
3. Open a PR to `home-assistant/brands` with files under:
   - `custom_integrations/hacomposablealarmclock/icon.png`
   - `custom_integrations/hacomposablealarmclock/logo.png`
4. After merge, clear browser/app cache and verify the integration tile icon in Home Assistant.

Until that PR merges, Home Assistant may continue to show a generic placeholder icon.