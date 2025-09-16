from .blog_service import BlogService
from .email_sevice import EmailService
from .free_form_service import FreeFormService
from .free_chat_service import FreeChatService
from .product_description_service import ProductDescriptionService
from .legal_gv_service import LegalGlobeViewService
from .dosha_quiz_service import DoshaQuizService

SERVICES_MAP = {
    "product_description": ProductDescriptionService(),
    "legal_gv": LegalGlobeViewService(),
    "email": EmailService(),
    "blog": BlogService(),
    "dosha_quiz": DoshaQuizService(),
    "free_form": FreeFormService(),
    "free_chat": FreeChatService(),
}
