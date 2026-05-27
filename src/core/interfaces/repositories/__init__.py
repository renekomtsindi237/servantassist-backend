"""
Interfaces de repositories (contracts) — Clean Architecture.

Toutes les interfaces utilisent typing.Protocol (subtyping structurel).
Les implémentations concrètes n'ont pas besoin d'hériter explicitement :
elles satisfont le protocole si elles possèdent les bonnes méthodes.
"""
from .api_key_repository import IApiKeyRepository
from .assignment_repository import IAssignmentRepository
from .attendance_repository import IAttendanceRepository
from .attendance_session_repository import IAttendanceSessionRepository
from .contribution_repository import IContributionRepository
from .cotisation_repository import ICotisationPeriodRepository, IMemberCotisationRepository
from .council_meeting_repository import ICouncilMeetingRepository
from .discipline_repository import IDisciplineCaseRepository
from .event_repository import IEventRepository
from .financial_entry_repository import IDiscrepancyRepository, IFinancialEntryRepository
from .invitation_repository import IInvitationRepository
from .material_repository import (
    IAubeTaskRepository,
    ICleaningTaskRepository,
    IMaintenanceHistoryRepository,
    IMaterialItemRepository,
    ITaskAssignmentRepository,
)
from .notification_repository import INotificationPreferenceRepository, INotificationRepository
from .report_repository import IAttachmentRepository, IReportRepository
from .responsable_repository import INominationRepository, IPosteActionRepository
from .sport_culture_repository import (
    IEventParticipationRepository,
    IEventResultRepository,
    IEventTeamRepository,
    ISportCultureEventRepository,
)
from .subgroup_repository import ISubGroupRepository
from .sunday_schedule_repository import ISundayScheduleRepository
from .training_repository import (
    ISessionMaterialRepository,
    ITrainingMaterialRepository,
    ITrainingParticipationRepository,
    ITrainingSessionRepository,
)
from .user_repository import IUserRepository
from .weekly_schedule_repository import IWeeklyScheduleRepository

__all__ = [
    "IApiKeyRepository",
    "IAssignmentRepository",
    "IAttachmentRepository",
    "IAttendanceRepository",
    "IAttendanceSessionRepository",
    "ICleaningTaskRepository",
    "IContributionRepository",
    "ICotisationPeriodRepository",
    "ICouncilMeetingRepository",
    "IDisciplineCaseRepository",
    "IEventParticipationRepository",
    "IEventRepository",
    "IEventResultRepository",
    "IEventTeamRepository",
    "IDiscrepancyRepository",
    "IFinancialEntryRepository",
    "IInvitationRepository",
    "IMaintenanceHistoryRepository",
    "IAubeTaskRepository",
    "IMaterialItemRepository",
    "IMemberCotisationRepository",
    "INotificationPreferenceRepository",
    "INotificationRepository",
    "INominationRepository",
    "IPosteActionRepository",
    "IReportRepository",
    "ISportCultureEventRepository",
    "ISubGroupRepository",
    "ISundayScheduleRepository",
    "ITaskAssignmentRepository",
    "ISessionMaterialRepository",
    "ITrainingMaterialRepository",
    "ITrainingParticipationRepository",
    "ITrainingSessionRepository",
    "IUserRepository",
    "IWeeklyScheduleRepository",
]
