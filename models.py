# models.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class BaseModel:
    """Базовый класс для всех моделей данных."""

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект модели в словарь."""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, list):
                    result[key] = value.copy()
                else:
                    result[key] = value
        return result

    def validate(self) -> tuple[bool, str]:
        """Проверяет валидность данных модели."""
        return True, ""

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.to_dict()})"

    def __repr__(self) -> str:
        return self.__str__()


class MLModel(BaseModel):
    """Модель для представления ML модели."""

    def __init__(self,
                 name: str,
                 algorithm: str,
                 version: str,
                 parameters: Optional[List[str]] = None,
                 model_id: Optional[int] = None,
                 created_at: Optional[datetime] = None):

        self.id = model_id
        self.name = name
        self.algorithm = algorithm
        self.version = version
        self.parameters = parameters or []
        self.created_at = created_at or datetime.now()

    def validate(self) -> tuple[bool, str]:
        """Проверяет валидность данных ML модели."""
        if not self.name or not self.name.strip():
            return False, "Название модели не может быть пустым"

        if len(self.name.strip()) > 100:
            return False, "Название модели не может превышать 100 символов"

        if not self.algorithm:
            return False, "Алгоритм должен быть указан"

        # Проверка формата версии (v1.0.0)
        import re
        if not re.match(r'^v\d+\.\d+\.\d+$', self.version):
            return False, "Версия должна быть в формате vX.Y.Z"

        return True, ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MLModel':
        """Создает объект MLModel из словаря."""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = None

        parameters = data.get('parameters', [])
        if isinstance(parameters, str):
            parameters = [p.strip() for p in parameters.strip('{}').split(',')] if parameters else []
        elif parameters is None:
            parameters = []

        return cls(
            name=data.get('name', ''),
            algorithm=data.get('algorithm', ''),
            version=data.get('version', ''),
            parameters=parameters,
            model_id=data.get('id'),
            created_at=created_at
        )


class Experiment(BaseModel):
    """Модель для представления эксперимента A/B тестирования."""

    def __init__(self,
                 name: str,
                 model_id: int,
                 attack_type: str,
                 is_active: bool = False,
                 user_count: int = 0,
                 success_rate: float = 0.0,
                 impressions: int = 0,
                 clicks: int = 0,
                 detection_threshold: float = 0.5,
                 status: str = 'planned',
                 experiment_id: Optional[int] = None,
                 created_at: Optional[datetime] = None):

        self.id = experiment_id
        self.name = name
        self.model_id = model_id
        self.attack_type = attack_type
        self.status = status
        self.is_active = is_active
        self.user_count = user_count
        self.success_rate = success_rate
        self.impressions = impressions
        self.clicks = clicks
        self.detection_threshold = detection_threshold
        self.created_at = created_at or datetime.now()

    def validate(self) -> tuple[bool, str]:
        """Проверяет валидность данных эксперимента."""
        if not self.name or not self.name.strip():
            return False, "Название эксперимента не может быть пустым"

        if len(self.name.strip()) > 100:
            return False, "Название эксперимента не может превышать 100 символов"

        if self.user_count < 0:
            return False, "Количество пользователей не может быть отрицательным"

        if self.impressions < 0:
            return False, "Количество показов не может быть отрицательным"

        if self.clicks < 0:
            return False, "Количество кликов не может быть отрицательным"

        if self.clicks > self.impressions:
            return False, "Количество кликов не может превышать количество показов"

        if self.success_rate < 0.0 or self.success_rate > 1.0:
            return False, "Процент успеха должен быть в диапазоне от 0.0 до 1.0"

        if self.detection_threshold < 0.0 or self.detection_threshold > 1.0:
            return False, "Порог обнаружения должен быть в диапазоне от 0.0 до 1.0"

        if self.model_id <= 0:
            return False, "Должна быть выбрана ML модель"

        valid_attack_types = ['ddos', 'malware', 'phishing', 'brute_force', 'zero_day']
        if self.attack_type not in valid_attack_types:
            return False, f"Тип атаки должен быть одним из: {', '.join(valid_attack_types)}"

        valid_statuses = ['planned', 'running', 'completed', 'failed', 'analyzing']
        if self.status not in valid_statuses:
            return False, f"Статус должен быть одним из: {', '.join(valid_statuses)}"

        return True, ""

    def calculate_ctr(self) -> float:
        """Вычисляет CTR (Click-Through Rate) в процентах."""
        if self.impressions <= 0:
            return 0.0
        return (self.clicks / self.impressions) * 100

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Experiment':
        """Создает объект Experiment из словаря."""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = None

        return cls(
            name=data.get('name', ''),
            model_id=data.get('model_id', 0),
            attack_type=data.get('attack_type', 'ddos'),
            status=data.get('status', 'planned'),
            is_active=data.get('is_active', False),
            user_count=data.get('user_count', 0),
            success_rate=data.get('success_rate', 0.0),
            impressions=data.get('impressions', 0),
            clicks=data.get('clicks', 0),
            detection_threshold=data.get('detection_threshold', 0.5),
            experiment_id=data.get('id'),
            created_at=created_at
        )


class ExperimentRun(BaseModel):
    """Модель для представления прогона эксперимента."""

    def __init__(self,
                 experiment_id: int,
                 duration_seconds: int,
                 accuracy: float,
                 precision_val: float,
                 recall_val: float,
                 f1_score: float,
                 false_positives: int,
                 false_negatives: int,
                 run_id: Optional[int] = None,
                 run_date: Optional[datetime] = None):

        self.id = run_id
        self.experiment_id = experiment_id
        self.duration_seconds = duration_seconds
        self.accuracy = accuracy
        self.precision_val = precision_val
        self.recall_val = recall_val
        self.f1_score = f1_score
        self.false_positives = false_positives
        self.false_negatives = false_negatives
        self.run_date = run_date or datetime.now()

    def validate(self) -> tuple[bool, str]:
        """Проверяет валидность данных прогона."""
        if self.duration_seconds <= 0:
            return False, "Длительность должна быть положительной"

        if not (0 <= self.accuracy <= 1):
            return False, "Accuracy должна быть между 0 и 1"

        if not (0 <= self.precision_val <= 1):
            return False, "Precision должна быть между 0 и 1"

        if not (0 <= self.recall_val <= 1):
            return False, "Recall должна быть между 0 и 1"

        if not (0 <= self.f1_score <= 1):
            return False, "F1-score должна быть между 0 и 1"

        if self.false_positives < 0:
            return False, "False positives не может быть отрицательным"

        if self.false_negatives < 0:
            return False, "False negatives не может быть отрицательным"

        if self.experiment_id <= 0:
            return False, "Должен быть указан experiment_id"

        return True, ""


# Вспомогательные функции
def create_experiment_from_form_data(form_data: Dict[str, Any]) -> Experiment:
    """Создает объект Experiment из данных формы."""
    return Experiment(
        name=form_data.get('name', '').strip(),
        model_id=int(form_data.get('model_id', 0)),
        attack_type=form_data.get('attack_type', 'ddos'),
        status=form_data.get('status', 'planned'),
        is_active=form_data.get('is_active', False),
        user_count=int(form_data.get('user_count', 0)),
        success_rate=float(form_data.get('success_rate', 0.0)),
        impressions=int(form_data.get('impressions', 0)),
        clicks=int(form_data.get('clicks', 0)),
        detection_threshold=float(form_data.get('detection_threshold', 0.5))
    )


def create_experiment_run_from_form_data(form_data: Dict[str, Any]) -> ExperimentRun:
    """Создает объект ExperimentRun из данных формы."""
    return ExperimentRun(
        experiment_id=int(form_data.get('experiment_id', 0)),
        duration_seconds=int(form_data.get('duration_seconds', 0)),
        accuracy=float(form_data.get('accuracy', 0.0)),
        precision_val=float(form_data.get('precision_val', 0.0)),
        recall_val=float(form_data.get('recall_val', 0.0)),
        f1_score=float(form_data.get('f1_score', 0.0)),
        false_positives=int(form_data.get('false_positives', 0)),
        false_negatives=int(form_data.get('false_negatives', 0))
    )


# Константы для валидации
ATTACK_TYPES = ['ddos', 'malware', 'phishing', 'brute_force', 'zero_day']
EXPERIMENT_STATUSES = ['planned', 'running', 'completed', 'failed', 'analyzing']
ALGORITHM_TYPES = ['random_forest', 'neural_network', 'svm', 'knn', 'decision_tree']