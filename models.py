import logging
from datetime import datetime
from typing import Optional, Dict, Any

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


class Experiment(BaseModel):
    """Модель для представления эксперимента A/B тестирования."""

    def __init__(self,
                 name: str,
                 is_active: bool = False,
                 user_count: int = 0,
                 success_rate: float = 0.0,
                 impressions: int = 0,
                 clicks: int = 0,
                 experiment_id: Optional[int] = None,
                 created_at: Optional[datetime] = None):

        self.id = experiment_id
        self.name = name
        self.is_active = is_active
        self.user_count = user_count
        self.success_rate = success_rate
        self.impressions = impressions
        self.clicks = clicks
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

        return True, ""

    def calculate_ctr(self) -> float:
        """Вычисляет CTR (Click-Through Rate) в процентах."""
        if self.impressions <= 0:
            return 0.0
        return (self.clicks / self.impressions) * 100

    def get_status(self) -> str:
        """Определяет статус эксперимента на основе данных."""
        if not self.is_active:
            return "Неактивный"

        ctr = self.calculate_ctr()
        if ctr > 5.0:
            return "Успешный"
        elif ctr > 1.0:
            return "Стабильный"
        else:
            return "Требует улучшений"

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
            is_active=data.get('is_active', False),
            user_count=data.get('user_count', 0),
            success_rate=data.get('success_rate', 0.0),
            impressions=data.get('impressions', 0),
            clicks=data.get('clicks', 0),
            experiment_id=data.get('id'),
            created_at=created_at
        )

    @classmethod
    def from_database_row(cls, row: tuple, columns: list) -> 'Experiment':
        """Создает объект Experiment из строки базы данных."""
        data = {}
        for i, column in enumerate(columns):
            data[column] = row[i]
        return cls.from_dict(data)


# Вспомогательные функции
def create_experiment_from_form_data(form_data: Dict[str, Any]) -> Experiment:
    """Создает объект Experiment из данных формы."""
    return Experiment(
        name=form_data.get('name', '').strip(),
        is_active=form_data.get('is_active', False),
        user_count=int(form_data.get('user_count', 0)),
        success_rate=float(form_data.get('success_rate', 0.0)),
        impressions=int(form_data.get('impressions', 0)),
        clicks=int(form_data.get('clicks', 0))
    )
