# Migrating from the former standalone dashboard cards

[← Back to README](../README.md) · [Advanced setup](advanced.md)

**Only existing users of the separate [`ha-infuse-cards`](https://github.com/Manantra/ha-infuse-cards) package need this guide.** New installations should install **Infuse Now Playing** alone: both cards are included and updated with the integration.

The final separate cards package **v0.1.4 (Legacy Bridge)** loads the bundled JavaScript from this integration, while keeping the older v0.1.3 code as a fallback for installations not yet updated. The existing `custom:infuse-now-playing-card` and `custom:infuse-household-card` card types, YAML configuration and Home Assistant entity IDs do **not** change.

## Migrate without interrupting your cards

1. Update the **Infuse Now Playing** integration to the latest release through HACS/Marketplace and restart Home Assistant.
2. Update the old **Infuse Dashboard Cards** package to its final **v0.1.4 (Legacy Bridge)** version. You can leave it installed temporarily: its loader imports the cards from `/api/infuse/cards/infuse-dashboard-cards.js`.
3. Refresh the Home Assistant frontend. Existing dashboards should now use the bundled version, including visual editors and subsequent card updates from the integration.

## Optional final cleanup

After verifying that the bridge works, remove the **separate cards package** using HACS/Marketplace. Remove only **legacy Infuse card resources** under **Settings → Dashboards → Resources**, such as:

- `/hacsfiles/ha-infuse-cards/` or `/local/community/ha-infuse-cards/`
- `/local/infuse-now-playing-card.js` or `/local/infuse-household-card.js`

**Do not delete unrelated resources.** Reload the Infuse integration or restart Home Assistant so that it registers its bundled resource. The integration does not delete HACS-managed resources itself, because HACS/Marketplace owns those entries.

If you previously copied the old JavaScript files to `/config/www/`, HACS does not update those copies. Remove the old manually registered resource and verify that the bundled module is the only active Infuse cards resource. Your dashboards, existing entity IDs, and automations remain unchanged.

### Lovelace YAML resource mode

Home Assistant does not let the integration automatically edit `configuration.yaml` when `lovelace: resource_mode: yaml` is used. Replace legacy resource entries with one bundled module resource and update its `?v=` cache-busting value whenever the integration version changes:

```yaml
lovelace:
  resource_mode: yaml
  resources:
    - url: /api/infuse/cards/infuse-dashboard-cards.js?v=0.2.15
      type: module
```

The module is served by the integration regardless of dashboard resource mode. For more details see [Advanced setup](advanced.md) or [Troubleshooting](troubleshooting.md).
