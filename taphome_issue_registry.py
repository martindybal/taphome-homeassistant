"""TapHome Issue Registry."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import IssueSeverity

from .const import TAPHOME_PLATFORM
from .translations import Issues


class TapHomeIssueRegistry:
    """TapHome Issue Registry."""

    def __init__(self, hass: HomeAssistant, core_id: str | None) -> None:
        """Initialize the TapHome Issue Registry."""
        self.hass = hass
        self.core_id = f" {core_id}" if core_id else ""

    def create_core_unavailable_issue(self) -> None:
        """Create an issue in the issue registry."""
        issue_id = self._create_core_unavailable_issue_id()
        self.create_issue(
            issue_id,
            is_fixable=False,
            severity=IssueSeverity.ERROR,
            translation_key=Issues.CORE_UNAVAILABLE,
            translation_placeholders={"core_id": str(self.core_id or "")},
        )

    def try_delete_core_unavailable_issue(self) -> None:
        """Try to delete a core unavailable issue."""
        issue_id = self._create_core_unavailable_issue_id()
        self.try_delete_issue(issue_id)

    def create_device_not_exposed_issue(self, taphome_device_id: int) -> None:
        """Create an issue in the issue registry."""
        issue_id = self._create_device_not_exposed_issue_id(taphome_device_id)
        self.create_issue(
            issue_id,
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            learn_more_url="https://taphome.com/support/601227274",
            translation_key=Issues.DEVICE_NOT_EXPOSED,
            translation_placeholders={
                "device_id": str(taphome_device_id),
                "core_id": self.core_id,
            },
        )

    def try_delete_device_not_exposed_issue(self, taphome_device_id: int) -> None:
        """Try to delete a device not exposed issue."""
        issue_id = self._create_device_not_exposed_issue_id(taphome_device_id)
        self.try_delete_issue(issue_id)

    def create_device_type_mismatch_issue(
        self,
        taphome_device_id: int,
        device_type: str,
        expected_device_types: str,
        supported_values: str,
    ) -> None:
        """Create an issue for a device with an unexpected type."""
        issue_id = self._create_device_type_mismatch_issue_id(taphome_device_id)
        self.create_issue(
            issue_id,
            is_fixable=False,
            severity=IssueSeverity.ERROR,
            translation_key=Issues.DEVICE_TYPE_MISMATCH,
            translation_placeholders={
                "device_id": str(taphome_device_id),
                "device_type": device_type,
                "expected": expected_device_types,
                "supported_values": supported_values,
                "core_id": self.core_id,
            },
        )

    def sync_new_device_issues(
        self, config_entry_id: str, hub, new_device_ids: set[int]
    ) -> None:
        """Create fixable issues for new devices and clear resolved ones."""
        registry = ir.async_get(self.hass)
        prefix = f"{Issues.NEW_DEVICE}_{config_entry_id}_"
        existing = {
            issue.issue_id
            for issue in registry.issues.values()
            if issue.domain == TAPHOME_PLATFORM and issue.issue_id.startswith(prefix)
        }
        wanted = {f"{prefix}{device_id}": device_id for device_id in new_device_ids}

        for issue_id in existing - set(wanted):
            self.try_delete_issue(issue_id)

        for issue_id, device_id in wanted.items():
            if issue_id in existing:
                continue
            device = hub.devices.get(device_id)
            device_name = device.name if device is not None else str(device_id)
            self.create_issue(
                issue_id,
                is_fixable=True,
                severity=IssueSeverity.WARNING,
                data={"config_entry_id": config_entry_id, "device_id": device_id},
                translation_key=Issues.NEW_DEVICE,
                translation_placeholders={
                    "device": f"{device_name} ({device_id})",
                    "core_id": self.core_id,
                },
            )

    def _create_device_not_exposed_issue_id(self, taphome_device_id):
        return f"{Issues.DEVICE_NOT_EXPOSED}_{taphome_device_id}"

    def _create_device_type_mismatch_issue_id(self, taphome_device_id):
        return f"{Issues.DEVICE_TYPE_MISMATCH}_{taphome_device_id}"

    def _create_core_unavailable_issue_id(self):
        return f"{Issues.CORE_UNAVAILABLE}_{self.core_id}"

    def create_issue(
        self,
        issue_id: str,
        *,
        breaks_in_ha_version: str | None = None,
        data: dict[str, str | int | float | None] | None = None,
        is_fixable: bool,
        is_persistent: bool = False,
        issue_domain: str | None = None,
        learn_more_url: str | None = None,
        severity: IssueSeverity,
        translation_key: str,
        translation_placeholders: dict[str, str] | None = None,
    ) -> None:
        """Create an issue in the issue registry."""

        def create_issue():
            ir.async_create_issue(
                self.hass,
                TAPHOME_PLATFORM,
                issue_id,
                breaks_in_ha_version=breaks_in_ha_version,
                data=data,
                is_fixable=is_fixable,
                is_persistent=is_persistent,
                issue_domain=issue_domain,
                learn_more_url=learn_more_url,
                severity=severity,
                translation_key=translation_key,
                translation_placeholders=translation_placeholders,
            )

        self.hass.loop.call_soon_threadsafe(create_issue)

    def try_delete_issue(self, issue_id: str) -> None:
        """Delete an issue from the issue registry when exist."""

        def delete_issue():
            return ir.async_delete_issue(self.hass, TAPHOME_PLATFORM, issue_id)

        self.hass.loop.call_soon_threadsafe(delete_issue)
