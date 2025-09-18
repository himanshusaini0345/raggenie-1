import os
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


load_dotenv()

class Configs(BaseSettings):
    # base
    ENV: str = os.getenv("ENV", "dev")
    API: str = "/api"
    PROJECT_NAME: str = "raggenie"

    DATABASE_URL: str = "sqlite:///raggenie.db"

    PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # database
    logging_enabled: bool = os.getenv("ENABLE_FILE_LOGGING", False)
    inference_llm_model:str = os.getenv("INFERENCE_LLM_MODEL", "gpt")
    groq_api_key:str = os.getenv("GROQ_API_KEY", "")
    secondary_inference_llm_model:str = os.getenv("SECONDARY_INFERENCE_LLM_MODEL", "llama4")

    # Auth
    auth_server: str = os.getenv("AUTH_SERVER", "0.0.0.0")
    username: str = os.getenv("ADMIN_USERNAME","admin")
    password: str = os.getenv("ADMIN_PASSWORD","password")
    secret_key: str = os.getenv("SECRET_KEY","secret")
    auth_enabled: bool = os.getenv("AUTH_ENABLED",False)
    default_username: str = os.getenv("DEFAULT_USERNAME", "Admin")
    
    client_private_key_file_path: str = os.getenv("CLIENT_PRIVATE_KEY_FILE_PATH", "app/providers/client-key-file.json")
    zitadel_token_url: str = os.getenv("ZITADEL_TOKEN_URL", "http://localhost:8080/oauth/v2/token")
    zitadel_domain: str = os.getenv("ZITADEL_DOMAIN", "http://localhost:8080")
    retry_limit:int = os.getenv("RETRY_LIMIT",1)
    application_port: int = os.getenv("APP_PORT", 8001)
    
    # Cache
    config_cache_limit: int = os.getenv("CONFIG_CACHE_LIMIT", 10)

    #Intents
    answer_from_enabled: bool = os.getenv("ANSWER_FROM_ENABLED",False)
    answer_from: str = os.getenv("ANSWER_FROM","database_agent")

    required_tables: List[str] = [
        "emp.Employees",
        "emp.EmpSalaryDetails",
        "emp.EmployeePFESIUNNO",
        "emp.EmployeeTDSForNonTeaching",
        "emp.vw_EmployeesList",
        "emp.FinalPayrollforNONTeaching",
        "emp.FinalPayrollforTeaching",
        "emp.FinalPayrollforStipend",
        "emp.RFIntrestForTeaching",
        "emp.Relatives",
        "emp.GatePass",
        "emp.vw_EducationDetailsList",
        "emp.vw_TicketingHeadList",
        "emp.BioAttendance",
        "emp.BioAttendanceTeaching",
        "emp.DocumentDetails",
        "emp.TeachingFinalPayRollVeryfication",
        "emp.LeaveDateWiseDetails",
        "emp.EarningsMappings",
        "emp.vw_LeaveDateWiseDeatilsList",
        "emp.vw_NomineesList",
        "emp.LeaveBalance",
        "emp.LeaveDetails",
        "emp.TicketingHead",
        "emp.DependentDetails",
        "emp.vw_WorkingExperienceList",
        "emp.vw_EmployeesAddressList",
        "emp.vw_EmployeesCovidVaccineList",
        "emp.vw_EmployeesListForAccommodation",
        "emp.TeachingLeaveBalance",
        "emp.PayRollSetting",
        "emp.WorkingExperience",

        "acom.ServicesCharges",
        "acom.ServiceMapping",
        "acom.AccommodationAllotment",
        "acom.BuildingMapping",
        "acom.RentalItemServicesCharges",
        "acom.vw_BuildingMappingList",
        "acom.vw_AccommodationAllotmentList",
        "acom.vw_AccommodationAvailabilityList",
        "acom.vw_AccommodationApplication",
        "acom.WifiService",

        "mst.AcademicCourses",
        "mst.PayCycle",
        "mst.Building",
        "mst.Department",
        "mst.FinancialYear",
        "mst.EmployeeDocumentType",
        "mst.EarningCategoryDetail",
        "mst.NoticeBoard",
        "mst.JobType",
        "mst.Designation",
        "mst.LeaveType",
        "mst.BioAttSift",
        "mst.TicketingDepartment",
        "mst.TicketingSubDepartment",
        "mst.ActionStatus",
        "mst.HolidayMaster",
        "mst.BloodGroup",
        "mst.Qualification",
        "mst.ServiceItems",
        "mst.ContractorDocumentType",
        "mst.YoutubeLiveStream",
        "mst.EmployeeDependent",

        "Vhc.BusAllotment",
        "Vhc.vw_BusAllotmentList",
        "Vhc.PetrolConception",
        "Vhc.DriverDetails",
        "Vhc.VehicleMaintenance",
        "Vhc.VehicleRegistration",
        "Vhc.BusStopage",

        "nac.vw_ActivityMonitoringList",
        "nac.ResearchPublicationType",

        "Usr.Users",
        "usr.UserRoles",
        "Usr.vw_RoleMenuPermissionList"
    ]
    user_roles: List[str] = [
        "account non-teaching",
        "account officer",
        "account stipend",
        "account teaching",
        "developer",
        "director",
        "finance officer",
        "hod-nt",
        "management",
        "non teaching loan",
        "os",
        "personal",
        "personal medical",
        "personal teaching",
        "principal",
        "rcm dept.",
        "security office",
        "senior finance officer",
        "stipend-os (medical)",
        "vice chancellor",
        "AI",
    ]


configs = Configs()
