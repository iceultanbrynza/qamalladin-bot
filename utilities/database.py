from lexicon import lexicon
from config import LOG_OFFSET
from qutypes import ProgressResult
from .other import generate_id

from .cloud import upload_file, get_url

from datetime import datetime

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

def get_student_id(db: Client, telegram:str):
    query = db.collection('students')\
              .where(filter=FieldFilter("telegram", "==", telegram))
    results = list(query.stream())

    if not results:
        print("⚠️ No documents found for this query.")

    elif len(results) > 1:
        print("⚠️ Student have duplicates in DB")

    else:
        doc = results[0]
        return doc.id

def query_card(db: Client, id:str, telegram:str)->dict:
    if id:
        doc = db.collection('students').document(id).get()
        if not doc.exists:
            return {}

    elif telegram:
        query = db.collection('students').where(filter=FieldFilter("telegram", "==", telegram))

        results = list(query.stream())

        if not results:
            print("⚠️ No documents found for this query.")
            return {}

        elif len(results) > 1:
            print("⚠️ Student have duplicates in DB")
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
    next_level = level_ref.get()

    if not next_level.exists:
        response = lexicon['ru']['database']["Student Completed"]
        return ProgressResult.FINISHED, response

    ref.update({
        "balance-per-level": 0,
        "level": next_level_ref
    })

    response = lexicon['ru']['database']["Student Completed The Level"]
    return ProgressResult.SUCCESS, response


def write_qcoins(qcoins:int, db: Client, mode, student_id, name, surname):
    if mode == 'id':
        doc_ref = db.collection('students').document(student_id)

        doc_ref.update({
            "balance": Increment(qcoins),
            "balance-per-level": Increment(qcoins)
        })
    if mode== 'fio':
        doc_ref = db.collection('students')
        query = doc_ref.where(filter=FieldFilter("name", "==", name))\
                       .where(filter=FieldFilter("surname", "==", surname))

        results = list(query.stream())

        if not results:
            print("⚠️ No documents found for this query.")
        else:
            for result in results:
                result.reference.update({
                    "balance": Increment(qcoins),
                    "balance-per-level": Increment(qcoins)
                })

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
    current_time = datetime.now()
    unique_id = str(current_time.strftime("%Y%m%d_%H%M%S"))
    public_id = f"{student_id}{task_id}{unique_id}"
    data = {unique_id: public_id, "is_checked": False}
    ref = db.collection('tasklogs').document('IT')\
        .collection(str(student_id)).document(str(task_id)).set(data, merge=True)
    response = upload_file(file, username, task_id, public_id, file_type)

def retrieve_task(db: Client, level: str, faculty:str) -> dict:
    try:
        ref = db.collection('tasks')\
                .document(faculty)\
                .collection(level)

        docs = ref.stream()
        tasks = {doc.id: doc.to_dict() for doc in docs}
        return tasks

    except NotFound:
        print(f"⚠️ Коллекция '{level}' не найдена.")
        return []

def retrieve_report(db:Client, student_id:str):
    ref = db.collection('tasklogs')\
            .document('IT')\
            .collection(student_id)\
            .where(filter=FieldFilter("is_checked", "==", False))

    docs = ref.stream()

    reports = {
        doc.id: {
            field: get_url(public_id)
            if isinstance(public_id, str) else public_id
            for field, public_id in doc.to_dict().items()}
        for doc in docs
    }

    return reports

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

        current_time = datetime.now()
        unique_id = str(current_time.strftime("%Y.%m.%d_%H:%M:%S.%f"))
        ref2 = db.collection('logs').document(unique_id)

        ref2.set({
            "task_id": task_id,
            "student": ref1,
            "created_at": datetime.now()
        })

        return True

    except GoogleAPICallError as e:
        print(lexicon['ru']['database']['Not Found 1'].format(task_id, student_id))
        return False

def get_log(db: Client, last_timestamp=None):
    try:
        ref = db.collection('logs')\
                .order_by('created_at', direction="DESCENDING")\

        if last_timestamp:
            ref = ref.start_after([last_timestamp])

        snapshots = list(ref.limit(LOG_OFFSET).stream())

        logs = [snap.to_dict() for snap in snapshots]

        if not snapshots:
            return {
                "logs": [],
                "last_timestamp": None
            }

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