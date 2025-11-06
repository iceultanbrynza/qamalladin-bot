from enum import Enum

class ProgressResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    FINISHED = "finished"
    STANDSTILL = 'standsill'

class PurchaseResult(Enum):
    SUCCESS = "✅ Успешная покупка!\nС баланса списано: {0}\nКуратор свяжется с тобой для получения награды."
    MISS = "⚠️ Не хватает средств на балансе."
    FAILED = "⚠️ Ошибка при оформлении покупки. Возможно, товар не доступен."

class AccrualResult(Enum):
    SUCCESS = "✅ Студенту {0} было начислено {1} qcoins"
    FINE_SUCCESS = "✅ Студенту {0} был оштрафован на {1} qcoins"
    DUBLICATE = "⚠️ Существует два и более студента с именем {0}. Пожалуйста, попробуйте найти нужного студента в списке с инлайн-кнопками"
    FAILED = "⚠️ Студент не найден"