from lexicon import lexicon
from config import LOG_OFFSET
from qutypes import ProgressResult, PurchaseResult, AccrualResult
from .other import (
    generate_id,
    generate_task_id,
)
from config import UserRole

from .cloud import *

from datetime import datetime
import pytz

from google.cloud.firestore import Client, Increment, FieldFilter
from google.api_core.exceptions import NotFound, GoogleAPICallError

def query_students(db: Client)->dict:
    students:dict = {}

    collection = db.collection('students')\
                   .order_by('surname', direction="ASCENDING")
    docs = collection.stream()

    for doc in docs:
        students[doc.id] = doc.to_dict()

    return students

def query_students_tags(db: Client)->list:
    students:list = []

    collection = db.collection('students')
    docs = collection.stream()

    for doc in docs:
        students.append(doc.to_dict().get('telegram', ''))

    return students

def query_curators_tags(db: Client)->list:
    curators:list = []

    collection = db.collection('curators')
    docs = collection.stream()

    for doc in docs:
        curators.append(doc.to_dict().get('telegram', ''))

    return curators

def get_student_id_name(db: Client, telegram:str):
    query = db.collection('students')\
              .where(filter=FieldFilter("telegram", "==", telegram))
    results = list(query.stream())

    if not results:
        print("⚠️ No documents found for this query.")

    elif len(results) > 1:
        print("⚠️ Student have duplicates in DB")

    else:
        snapshot = results[0]
        doc = snapshot.to_dict()
        name =  doc.get("surname") + " " + doc.get("name")
        return snapshot.id, name

def query_card(db: Client, id:str, telegram:str)->dict:
    if id:
        doc = db.collection('students')\
                .document(id)\
                .get()
        if not doc.exists:
            return {}

    elif telegram:
        query = db.collection('students').where(filter=FieldFilter("telegram", "==", telegram))

        results = list(query.stream())

        if not results:
            return {}

        elif len(results) > 1:
            return {}

        else:
            doc = results[0]

    snapshot = doc.to_dict()
    # query level of the student
    level_ref = snapshot.get('level')
    level_snapshot = level_ref.get()

    if not level_snapshot.exists:
        return {}

    snapshot['level'] = level_snapshot.to_dict().get('number')
    snapshot['goal'] = level_snapshot.to_dict().get('goal')
    return snapshot

def query_level_goal(db:Client, id)->bool:
    doc = db.collection('students').document(id).get()

    if not doc.exists:
        return None

    snapshot = doc.to_dict()

    balance_per_level = snapshot.get('balance-per-level', '')
    level_ref = snapshot.get('level', '')

    if not balance_per_level and not level_ref:
        return None

    level_snapshot = level_ref.get()
    goal = level_snapshot.to_dict().get('goal')

    return True if balance_per_level >= goal else False

def move_to_next_level(db:Client, student_id)->tuple[ProgressResult, str]:
    ref = db.collection('students').document(student_id)
    doc = ref.get()
    if not doc.exists:
        response = lexicon['ru']['database']["Student Not Found"].format(student_id)
        return ProgressResult.FAILED, response

    snapshot = doc.to_dict()
    level_ref = snapshot.get('level')
    level_snapshot = level_ref.get()

    if not level_snapshot.exists:
        response = lexicon['ru']['database']["Level Not Found"].format(student_id)
        return ProgressResult.FAILED, response

    level_number = level_snapshot.to_dict().get('number')
    next_level_ref = db.collection('levels')\
                       .document(str(level_number+1))
    next_level = next_level_ref.get()

    next_next_level_ref = db.collection('levels')\
                            .document(str(level_number+2))
    next_next_level = next_next_level_ref.get()

    if not next_level.exists and not next_next_level.exists:
        return ProgressResult.FINISHED, None

    elif not next_next_level.exists:
        response = lexicon['ru']['database']["Student Completed"]
        ref.update({
            "balance-per-level": 0,
            "level": next_level_ref
        })
        return ProgressResult.FINISHED, response

    ref.update({
        "balance-per-level": 0,
        "level": next_level_ref
    })

    response = lexicon['ru']['database']["Student Completed The Level"]
    return ProgressResult.SUCCESS, response

def write_qcoins(qcoins:int, db: Client, mode, student_id, name, surname):
    try:
        if mode == 'id':
            doc_ref = db.collection('students').document(student_id)
            doc = doc_ref.get()
            if not doc.exists:
                return AccrualResult.FAILED, AccrualResult.FAILED.value

            doc_ref.update({
                "balance": Increment(qcoins),
                "balance-per-level": Increment(qcoins)
            })

            if qcoins >= 0:
                return AccrualResult.SUCCESS, AccrualResult.SUCCESS.value.format(student_id, qcoins)

            elif qcoins < 0:
                return AccrualResult.SUCCESS, AccrualResult.FINE_SUCCESS.value.format(student_id, qcoins)

        elif mode== 'fio':
            full_name = name + " " + surname
            doc_ref = db.collection('students')
            query = doc_ref.where(filter=FieldFilter("name", "==", name))\
                        .where(filter=FieldFilter("surname", "==", surname))

            results = list(query.stream())

            if not results:
                return AccrualResult.FAILED, AccrualResult.FAILED.value

            if len(results) > 1:
                return AccrualResult.DUBLICATE, AccrualResult.DUBLICATE.value

            else:
                result = results[0]
                result.reference.update({
                    "balance": Increment(qcoins),
                    "balance-per-level": Increment(qcoins)
                })

                if qcoins >= 0:
                    return AccrualResult.SUCCESS, AccrualResult.SUCCESS.value.format(full_name, qcoins)

                elif qcoins < 0:
                    return AccrualResult.SUCCESS, AccrualResult.FINE_SUCCESS.value.format(full_name, qcoins)

        else:
            return AccrualResult.FAILED, AccrualResult.FAILED.value

    except ValueError:
        return AccrualResult.VALUE_ERROR, AccrualResult.VALUE_ERROR.value

    except Exception as e:
        response = AccrualResult.FAILED.value + "\n" + str(e)
        return AccrualResult.FAILED, response

def add_fine(db:Client, mode, student_id, name, surname):
    try:
        if mode == 'id':
            doc_ref = db.collection('students').document(student_id)
            doc = doc_ref.get()

            if not doc.exists:
                return False

            doc_ref.update({'fine': Increment(1)})
            return True

        elif mode=='fio':
            doc_ref = db.collection('students')
            query = doc_ref.where(filter=FieldFilter("name", "==", name))\
                        .where(filter=FieldFilter("surname", "==", surname))

            results = list(query.stream())

            if not results:
                return False

            result = results[0]
            result.reference.update({
                "fine": Increment(1)
            })
            return True

    except NotFound:
            return False

def send_task(db: Client, username, task_id, file, student_id, file_type):
    try:
        tz = pytz.timezone("Asia/Almaty")
        current_time = datetime.now(tz)
        unique_id = str(current_time.strftime("%Y%m%d_%H%M%S"))
        public_id = f"{student_id}{task_id}{unique_id}"
        data = {unique_id: public_id, "is_checked": False}
        ref = db.collection('tasklogs')\
                .document('IT')\
                .collection(str(student_id))\
                .document(str(task_id))\
                .set(data, merge=True)
        response = upload_file(file, username, task_id, public_id, file_type)
        return True

    except:
        return False

def retrieve_task(db: Client, level: str, faculty:str, completed_tasks:list[str]) -> dict:
    try:
        ref = db.collection('tasks')\
                .document(faculty)\
                .collection(level)\

        if completed_tasks:
            ref = ref.where(filter=FieldFilter("id", "not-in",completed_tasks))

        docs = ref.stream()
        docs_list = list(docs)

        if not docs_list:
            return {}

        tasks = {doc.id: doc.to_dict() for doc in docs_list}
        return tasks

    except NotFound:
        return {}

def retrieve_report(db:Client, student_id:str):
    try:
        ref = db.collection('tasklogs')\
                .document('IT')\
                .collection(student_id)\
                .where(filter=FieldFilter("is_checked", "==", False))

        docs = ref.stream()
        docs_list = list(docs)
        if not docs_list:
            return {}

        reports = {
            doc.id: {
                field: get_url(public_id)
                if isinstance(public_id, str) else public_id
                for field, public_id in doc.to_dict().items()}
            for doc in docs_list
        }

        return reports

    except:
        return {}

def retrieve_completed_tasks_by_student(db:Client, student_id)->list:
    try:
        ref = db.collection('tasklogs')\
                .document('IT')\
                .collection(student_id)
        docs = ref.stream()

        task_ids = [doc.id for doc in docs]
        return task_ids

    except:
        return []

def mark_as_chekched(db:Client, student_id:str, task_id:str):
    try:
        ref = db.collection('tasklogs')\
                .document('IT')\
                .collection(student_id)\
                .document(task_id)\
                .update({"is_checked": True})

        ref = db.collection('students')\
                .document(student_id)\
                .update({"tasks": Increment(1)})

        return True

    except NotFound:
        print(lexicon['ru']['database']['Not Found 1'].format(task_id, student_id))
        return False

def write_log(db: Client, student_id:str, task_id:str=None):
    try:
        ref1 = db.collection('students')\
                 .document(student_id)
        doc = ref1.get()

        if not doc.exists:
            print(lexicon['ru']['database']['Student Not Found'].format(student_id))
            return False
        tz = pytz.timezone("Asia/Almaty")
        current_time = datetime.now(tz)
        unique_id = str(current_time.strftime("%Y.%m.%d_%H:%M:%S.%f"))
        ref2 = db.collection('logs').document(unique_id)

        ref2.set({
            "task_id": task_id,
            "student": ref1,
            "created_at": current_time
        })

        return True

    except GoogleAPICallError as e:
        print(lexicon['ru']['database']['Not Found 1'].format(task_id, student_id))
        return False

def get_log(db: Client, student_id=None, last_timestamp=None):
    try:
        if student_id is not None:
            student_ref = db.collection("students")\
                            .document(student_id)
            ref = db.collection('logs')\
                .where(filter=FieldFilter("student", "==", student_ref))\
                .order_by('created_at', direction="DESCENDING")

        else:
            ref = db.collection('logs')\
                    .order_by('created_at', direction="DESCENDING")

        if last_timestamp:
            ref = ref.start_after([last_timestamp])

        snapshots = list(ref.limit(LOG_OFFSET).stream())

        if not snapshots:
            return {
                "logs": [],
                "last_timestamp": None
            }

        logs = [snap.to_dict() for snap in snapshots]

        last_timestamp = snapshots[-1].to_dict().get("created_at")

        return {
            "logs": logs,
            "last_timestamp": last_timestamp
        }

    except NotFound:
        print(lexicon['ru']['database']['Not Found 2'].format(last_timestamp))
        return False

def add_student(db: Client, year:int, student:str):
    name = student[1]
    surname = student[0]
    faculty = student[2]
    telegram = student[3]

    level = db.collection('levels')\
              .document('1')

    id = generate_id(year, faculty)

    document_data = {
        'name': name,
        'surname': surname,
        'faculty': faculty,
        'telegram': telegram,
        'level': level,
        'year': year,
        'balance': 0,
        'balance-per-level':0,
        'tasks': 0,
        'fine': 0
    }

    db.collection('students')\
      .document(id)\
      .set(document_data)

def add_curator(db:Client, surname, name, telegram):
    try:
        year = datetime.now().year
        curator_id = generate_id(year, "QU")
        ref = db.collection("curators")\
                .document(curator_id)\
                .set({
                    "surname": surname,
                    "name": name,
                    "telegram": telegram
                })
        return True

    except:
        return False

def delete_curator(db:Client, telegram):
    try:
        ref = db.collection("curators")\
                .where(filter=FieldFilter("telegram", "==", telegram))

        results = list(ref.stream())

        if not results:
            return False

        for result in results:
            result.reference.delete()

        return True

    except:
        return False

def delete_student(db:Client, telegram):
    try:
        ref = db.collection("students")\
                .where(filter=FieldFilter("telegram", "==", telegram))

        results = list(ref.stream())

        if not results:
            return False

        for result in results:
            result.reference.delete()

        return True

    except:
        return False

def add_level(db:Client, level):
    number = int(level[0])
    title = level[1]
    league = level[2]
    goal = int(level[3])

    document_data = {
        'number': number,
        'title': title,
        'league': league,
        'goal': goal
    }

    db.collection('levels')\
      .document(str(number))\
      .set(document_data)

def add_task(db:Client, faculty, level, block, number, content):
    id = generate_task_id(faculty, level, block, number)

    document_data = {
        'number': int(number),
        'content': content,
        'block': block,
        'id': id
    }

    db.collection('tasks')\
      .document(faculty)\
      .collection(str(level))\
      .document(id)\
      .set(document_data)

def record_chat_id(db:Client, username:str, role: UserRole, chat_id:str):
    if role == UserRole.CURATOR:
        ref = db.collection('curators')\
                .where(filter=FieldFilter(
                    "telegram", "==", username
                ))

    elif role == UserRole.STUDENT:
        ref = db.collection('students')\
                .where(filter=FieldFilter(
                    "telegram", "==", username
                ))

    results = list(ref.stream())
    if not results:
        return False

    else:
        for result in results:
            result.reference.update({
                "chat_id": chat_id
            })
        return True

def get_student_id_for_curator(db:Client, name, surname):
    try:
        doc_ref = db.collection('students')
        query = doc_ref.where(filter=FieldFilter("name", "==", name))\
                    .where(filter=FieldFilter("surname", "==", surname))

        results = list(query.stream())

        if not results:
            return ProgressResult.FAILED

        elif len(results) > 1:
            return ProgressResult.DUBLICATE

        else:
            result = results[0]
            student_id = result.id
            return student_id if student_id else ProgressResult.FAILED

    except:
        return ProgressResult.FAILED

def delete_task(db:Client, student_id, task_id):
    try:
        ref = db.collection("tasklogs")\
                .document("IT")\
                .collection(student_id)\
                .document(task_id)
        ref.delete()

    except:
        return

def write_accrual_to_log(db:Client, qcoins, student_id, task_id=None):
    try:
        tz = pytz.timezone("Asia/Almaty")
        student_ref = db.collection("students")\
                        .document(student_id)

        if task_id is not None:
            ref = db.collection('logs')\
                    .where(filter=FieldFilter("student", "==", student_ref))\
                    .where(filter=FieldFilter("task_id", "==", task_id))\
                    .order_by('created_at', direction="DESCENDING")

            results = list(ref.stream())

            if not results:
                current_time = datetime.now(tz)
                unique_id = str(current_time.strftime("%Y.%m.%d_%H:%M:%S.%f"))
                db.collection('logs').document(unique_id).set({
                    "accrual": qcoins,
                    "student": student_ref,
                    "task_id": task_id,
                    "created_at": datetime.now(tz),
                    "accrualed_at": datetime.now(tz)
                })

                return unique_id

            result = results[0]
            result.reference.update({
                "accrual": int(qcoins),
                "accrualed_at": datetime.now(tz)
            })

            return result.id

        else:
            current_time = datetime.now(tz)
            unique_id = str(current_time.strftime("%Y.%m.%d_%H:%M:%S.%f"))
            ref2 = db.collection('logs').document(unique_id)

            ref2.set({
                "accrual": int(qcoins),
                "student": student_ref,
                "created_at": datetime.now(tz),
                "accrualed_at": datetime.now(tz)
            })

            return unique_id

    except Exception as e:
        return False

def query_goods(db: Client):
    response = {}

    ref = db.collection('shop')
    goods = list(ref.stream())

    for good in goods:
        response[good.id] = good.to_dict()

    return response

def upload_goods(db: Client, data, photo, public_id):
    try:
        upload_good_file(photo, public_id)

        id = generate_id(2025, "S")
        ref = db.collection("shop")\
                .document(id)\
                .set(data)
        return True

    except:
        return False

def purchase(db: Client, student_id:str, good_id:str):
    try:
        student_ref = db.collection("students")\
                        .document(student_id)
        student = student_ref.get().to_dict()
        balance:int = student.get("balance")

        good_ref = db.collection("shop")\
                .document(good_id)
        good = good_ref.get()
        good_dict = good.to_dict()
        price = int(good_dict.get("price"))

        if good.exists and balance >= price:
            import pytz
            tz = pytz.timezone("Asia/Almaty")
            current_time = datetime.now(tz)
            unique_id = str(current_time.strftime("%Y.%m.%d_%H:%M:%S.%f"))
            ref2 = db.collection('logs').document(unique_id)

            ref2.set({
                "good_id": good_ref,
                "student": student_ref,
                "created_at": datetime.now(tz),
                "expenditure": price
            })

            student_ref.update({"balance": balance - price})
            return PurchaseResult.SUCCESS, PurchaseResult.SUCCESS.value.format(price)

        elif not good.exists:
            return PurchaseResult.FAILED, PurchaseResult.FAILED.value

        elif balance < price:
            return PurchaseResult.MISS, PurchaseResult.MISS.value

    except:
        return PurchaseResult.FAILED, PurchaseResult.FAILED.value

def get_good_desc(student_name, good_id, time):
    try:
        good = good_id.get().to_dict()
        expenditure = good.get("price")
        name = good.get("name")
        msg = f"{time}: {student_name} приобрел {name} за {expenditure} Qcoins"
        return msg

    except:
        return None

def delete_good(db: Client, good_id):
    try:
        ref = db.collection("shop")\
                .document(good_id)

        ref.delete()
        return True

    except:
        return False

def write_comment(db: Client, log_id:str, comment:str):
    try:
        ref = db.collection("logs")\
                .document(log_id)

        doc = ref.get()

        if not doc.exists:
            return False

        ref.update({
            "comment": comment
        })

        return True

    except:
        return False