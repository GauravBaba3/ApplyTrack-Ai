"""
Staleness & Follow-Up Intelligence Service for ApplyTrack AI.

Monitors active applications for inactivity over configurable thresholds:
- 7 days: Stale / Active follow-up opportunity
- 14 days: No Response
- 30 days: Possible Ghosting (Never silently marked as rejection)

Generates tailored, professional follow-up drafts.
Strict Policy: Zero automatic email sending in MVP. User must review and send.
"""
import logging
from datetime import timedelta
from typing import List, Dict, Any, Optional
from django.utils import timezone

from apps.applications.models import Application, ApplicationStatus, FollowUp, StatusHistory

logger = logging.getLogger(__name__)


class StalenessService:
    """
    Service for identifying stale applications and drafting follow-up emails.
    """

    STALE_DAYS_THRESHOLD = 7
    NO_RESPONSE_DAYS_THRESHOLD = 14
    GHOSTING_DAYS_THRESHOLD = 30

    @classmethod
    def audit_user_applications_for_staleness(cls, user) -> Dict[str, Any]:
        """
        Audit all active applications for a user and flag stale/ghosted states.
        """
        now = timezone.now()
        active_statuses = [
            ApplicationStatus.APPLIED,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.ASSESSMENT,
            ApplicationStatus.INTERVIEW
        ]

        apps = Application.objects.filter(
            user=user,
            current_status__in=active_statuses
        )

        stale_count = 0
        no_response_count = 0
        ghosted_count = 0
        drafted_count = 0

        for app in apps:
            ref_date = app.last_activity_date or app.status_updated_at or timezone.make_aware(
                timezone.datetime.combine(app.application_date, timezone.datetime.min.time())
            )
            days_inactive = (now - ref_date).days

            if days_inactive >= cls.GHOSTING_DAYS_THRESHOLD:
                ghosted_count += 1
                if app.current_status != ApplicationStatus.GHOSTED:
                    # Update status to Ghosted with history entry
                    prev = app.current_status
                    app.current_status = ApplicationStatus.GHOSTED
                    app.notes = f"Auto-tagged as Possible Ghosting after {days_inactive} days of silence."
                    app.save(update_fields=['current_status', 'notes', 'updated_at'])

                    StatusHistory.objects.create(
                        application=app,
                        previous_status=prev,
                        new_status=ApplicationStatus.GHOSTED,
                        source='staleness_monitor',
                        confidence=0.85,
                        evidence=f"No activity for {days_inactive} days (threshold: {cls.GHOSTING_DAYS_THRESHOLD}d)"
                    )
            elif days_inactive >= cls.NO_RESPONSE_DAYS_THRESHOLD:
                no_response_count += 1
                if app.current_status == ApplicationStatus.APPLIED:
                    app.current_status = ApplicationStatus.NO_RESPONSE
                    app.save(update_fields=['current_status', 'updated_at'])

                    StatusHistory.objects.create(
                        application=app,
                        previous_status=ApplicationStatus.APPLIED,
                        new_status=ApplicationStatus.NO_RESPONSE,
                        source='staleness_monitor',
                        confidence=0.90,
                        evidence=f"No response for {days_inactive} days since application"
                    )
            elif days_inactive >= cls.STALE_DAYS_THRESHOLD:
                stale_count += 1

            # Generate follow-up draft if none exists yet
            if days_inactive >= cls.STALE_DAYS_THRESHOLD and not app.follow_ups.filter(is_sent=False).exists():
                cls.generate_follow_up_draft(app, days_inactive=days_inactive)
                drafted_count += 1

        return {
            'total_audited': apps.count(),
            'stale_count': stale_count,
            'no_response_count': no_response_count,
            'ghosted_count': ghosted_count,
            'follow_up_drafts_created': drafted_count
        }

    @classmethod
    def generate_follow_up_draft(
        cls,
        application: Application,
        days_inactive: int = 7
    ) -> FollowUp:
        """
        Generate a contextual, polite follow-up draft for the user to review and send.
        """
        company = application.company
        role = application.job_title
        contact_name = application.recruiter_name or "Hiring Team"

        subject = f"Following up on application for {role} at {company}"

        body = (
            f"Dear {contact_name},\n\n"
            f"I hope you are having a wonderful week.\n\n"
            f"I am writing to follow up on my application for the {role} position at {company}, "
            f"which I submitted recently. I remain very enthusiastic about the opportunity to contribute "
            f"to your team's goals.\n\n"
            f"Please let me know if there are any additional details, portfolio links, or references I can provide "
            f"to assist with your evaluation.\n\n"
            f"Thank you very much for your time and consideration. I look forward to hearing from you.\n\n"
            f"Best regards,\n"
            f"{application.user.get_full_name() or application.user.username}"
        )

        suggested_date = (timezone.now() + timedelta(days=1)).date()

        follow_up = FollowUp.objects.create(
            application=application,
            draft_subject=subject,
            draft_body=body,
            suggested_send_date=suggested_date,
            days_stale=days_inactive,
            is_sent=False
        )

        logger.info(f"Generated follow-up draft for application {application.id} ({company})")
        return follow_up
