from .cloud import upload_file, get_url

from datetime import datetime

from google.cloud.firestore import Client, Increment, FieldFilter
from google.api_core.exceptions import NotFound

def query_students(db: Client)->dict:
    students:dict = {}

    collection = db.collection('students')
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
    query = db.collection('students').where(filter=FieldFilter("telegram", "==", telegram))
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

        elif len(results) > 1:
            print("⚠️ Student have duplicates in DB")

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

def write_qcoins(qcoins:int, db: Client, mode, student_id, name, surname):
    if mode == 'id':
        doc_ref = db.collection('students').document(student_id)

        doc_ref.update({
            "balance": Increment(qcoins)
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
                    "balance": Increment(qcoins)
                })

def send_task(db: Client, username, task_id, file, student_id, file_type):
    current_time = datetime.now()
    unique_id = str(current_time.strftime("%Y%m%d_%H%M%S"))
    public_id = f"{student_id}{task_id}{unique_id}"
    data = {unique_id: public_id, "is_checked": False}
    ref = db.collection('tasklogs').document('IT')\
        .collection(str(student_id)).document(str(task_id)).set(data, merge=True)
    upload_file(file, username, task_id, public_id, file_type)

def retrieve_task(db: Client, level: str, faculty:str) -> dict:
    try:
        ref = db.collection('tasks').document(faculty).collection(level)
        docs = ref.stream()
        tasks = {doc.id: doc.to_dict() for doc in docs}
        return tasks

    except NotFound:
        print(f"⚠️ Коллекция '{level}' не найдена.")
        return []

def retrieve_report(db:Client, student_id:str):
    ref = db.collection('tasklogs').document('IT').collection(student_id)
    docs = ref.stream()

    reports = {
        doc.id: {
            field: get_url(public_id)
            if isinstance(public_id, str) else public_id
            for field, public_id in doc.to_dict().items()}
        for doc in docs
    }

    return reports
