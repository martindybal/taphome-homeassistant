"""TapHome Issue Registry."""

from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.issue_registry import HomeAssistant, IssueSeverity

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

    def _create_device_not_exposed_issue_id(self, taphome_device_id):
        return f"{Issues.DEVICE_NOT_EXPOSED}_{taphome_device_id}"

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
