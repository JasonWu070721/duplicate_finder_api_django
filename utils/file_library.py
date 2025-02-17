# -*- coding: UTF-8 -*-
import os
import hashlib
import logging
import sys
from os import walk
import json
import os
from pathlib import PurePath
from file.models import File
from file.serializers import FileSerializer

from file.models import SearchResult
from file.serializers import SearchResultSerializer

IF_SAVE_CHECKSUM = True
OS_TYPE = "synology"  # synology, windows
IS_CLEAR_FILE_TABLE = True
DELETE_REPEAT_FILE = False


class FileInit:
    log_file = "findIdenticalFiles.log"
    file_total = 0
    file_count = 0

    def logger(self):
        logger = logging.getLogger()
        if not logger.handlers:
            formatter = logging.Formatter("%(asctime)s %(levelname)-8s: %(message)s")

            file_handler = logging.FileHandler(self.log_file)
            file_handler.setFormatter(formatter)

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.formatter = formatter

            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            logger.setLevel(logging.INFO)
        return logger

    def is_json(self, myjson):
        try:
            json.loads(myjson)
        except ValueError as e:
            return False
        return True

    def get_md5(self, filename):
        m = hashlib.md5()
        md5_value = None
        mfile = open(filename, "rb")
        if mfile.readable():
            m.update(mfile.read())
            mfile.close()
            md5_value = m.hexdigest()
        return md5_value

    def get_blake2(self, filename):
        m = hashlib.blake2b()
        blake2_value = None
        mfile = open(filename, "rb")
        if mfile.readable():
            m.update(mfile.read())
            mfile.close()
            blake2_value = m.hexdigest()
        return blake2_value

    def check_file_statuses_same(
        self, file_path, file_size, file_mtime, file_ctime, file_blake2=None
    ):
        if not os.path.isfile(file_path):
            return False

        if IF_SAVE_CHECKSUM:
            _blake2 = self.get_blake2(file_path)

            if file_blake2 == _blake2:
                return True
        else:
            _file_size = os.path.getsize(file_path)
            _file_mtime = os.path.getmtime(file_path)
            _file_ctime = os.path.getctime(file_path)

            if (
                file_size == _file_size
                and file_mtime == _file_mtime
                and file_ctime == _file_ctime
            ):
                return True

        return False

    def check_file_modified(self, file_path):
        """
        The function is to check file is modified or not.
        Parameters:
        file_path (str): file path

        Returns:
        0 (int): if file is not changed
        -1 (int): if file is in db
        > 0 (int): if file is modified
        """

        files_db = self.get_file_db(file_path)

        if files_db and len(files_db) > 0:
            file_blake2 = None
            files_db = files_db[0]
            file_size = files_db["size"]
            file_mtime = files_db["mtime"]
            file_ctime = files_db["ctime"]
            if IF_SAVE_CHECKSUM:
                file_blake2 = files_db["hash_md5"]

            file_is_same = self.check_file_statuses_same(
                file_path, file_size, file_mtime, file_ctime, file_blake2
            )

            if file_is_same:
                return "same", None
            else:
                return "fined", files_db

        return "not_fined", None

    def get_file_info(self, file_path, get_md5=False):
        file_md5 = None
        file_status = None
        isFile = os.path.isfile(file_path)

        if isFile:
            file_size = os.path.getsize(file_path)
            file_mtime = os.path.getmtime(file_path)
            file_ctime = os.path.getctime(file_path)
            file_name, file_extension = os.path.splitext(file_path)

            file_extension = file_extension.lower()

            file_status = {
                "name": file_name,
                "full_path": file_path,
                "hash_md5": file_md5,
                "size": file_size,
                "mtime": file_mtime,
                "ctime": file_ctime,
                "extension": file_extension,
            }

        return file_status

    def save_file_status_in_db(self, root_path):
        file_count = 0

        for root, _, files in walk(os.path.normpath(root_path)):
            if OS_TYPE == "synology" and "@eaDir" in root:
                continue

            for file in files:
                path = os.path.join(root, file)
                path = os.path.normpath(path)

                file_object = File(file_path=path)
                file_object.save()
                file_count += 1
                if (file_count / 200).is_integer():
                    print("file count:", file_count)

        return file_count

    def get_file_count(self, root_path):
        file_count = 0
        for _, _, _ in walk(os.path.normpath(root_path)):
            file_count += 1
            if (file_count / 100).is_integer():
                print("file count:", file_count)
        return file_count

    def save_file_path_in_db(self, root_path):
        file_count = 0

        for root, _, files in walk(os.path.normpath(root_path)):
            if OS_TYPE == "synology" and "@eaDir" in root:
                continue

            for file in files:
                path = os.path.join(root, file)
                path = os.path.normpath(path)

                file_object = File(file_path=path)
                file_object.save()
                file_count += 1
                if (file_count / 200).is_integer():
                    print("file count:", file_count)

        return file_count

    def get_all_files(self, root_path):
        file_count = 0
        file_list = []
        for root, _, files in walk(os.path.normpath(root_path)):
            if OS_TYPE == "synology" and "@eaDir" in root:
                continue

            for file in files:
                path = os.path.join(root, file)
                path = os.path.normpath(path)

                file_count += 1
                if (file_count / 200).is_integer():
                    print("file count:", file_count)
                file_list.append(path)

        return file_list

    def order_file_table(self, column_name):
        files_db = None

        try:
            files_db = File.objects.order_by(column_name)
        except Exception as e:
            print("order file table is fault, error:", e)
            return None

        return files_db

    def get_file_db(self, file_path):
        db_return = None

        if file_path:
            try:
                queryset = File.objects.filter(file_path=file_path)
                serializer = FileSerializer(queryset, many=True)
                db_return = serializer.data
            except Exception as e:
                print("get file is fault, error:", e)

        return db_return

    def update_file_status_in_db(self, file_path, file_id):
        file_info = self.get_file_info(file_path, get_md5=IF_SAVE_CHECKSUM)
        if file_info:
            file_md5 = None
            file_size = file_info["size"]
            file_mtime = file_info["mtime"]
            file_ctime = file_info["ctime"]
            if IF_SAVE_CHECKSUM:
                file_md5 = file_info["hash_md5"]
            try:
                File.objects.filter(id=file_id).update(
                    size=file_size,
                    mtime=file_mtime,
                    ctime=file_ctime,
                    hash_md5=file_md5,
                )
            except Exception as e:
                print("update file is fault, error:", e)

        return

    def save_file_status(self, file_path):
        file_status = None

        try:
            file_status = self.get_file_info(file_path, get_md5=IF_SAVE_CHECKSUM)
        except Exception as e:
            print("get-file-info is fault, error: ", e)

        serializer = FileSerializer(data=file_status)

        is_valid = serializer.is_valid(raise_exception=True)

        if is_valid:
            db_return = serializer.validated_data

            file_name = db_return["name"]
            file_size = db_return["size"]
            file_mtime = db_return["mtime"]
            file_ctime = db_return["ctime"]
            file_md5 = db_return["hash_md5"]
            file_extension = db_return["extension"]

            try:
                file_object = File(
                    name=file_name,
                    size=file_size,
                    mtime=file_mtime,
                    ctime=file_ctime,
                    hash_md5=file_md5,
                    full_path=file_path,
                    extension=file_extension,
                )
                file_object.save()
            except Exception as e:
                print("create file is fault, error:", e)

        return

    def get_same_file_group(self):

        if not self.update_group_ids_by_file_size():
            return False

        if not self.update_group_ids_by_blake2_hash():
            return False

        if not self.regroup_id():
            return False

        return True

    def regroup_id(self):
        insertQuery = """
                SELECT 
                    id,
                    group_id,
                    hash_blake2,
                    hash_md5,
                    created_at,
                    updated_at
                FROM file_searchresult fs 
                ORDER BY hash_blake2 ASC;
            """

        try:
            data = SearchResult.objects.raw(insertQuery)
        except Exception as e:
            print("get SearchResult is fault, error:", e)
            return False

        pre_blake2_hash = None
        group_id = 0

        for row in data:
            blake2_hash = row.hash_blake2

            if pre_blake2_hash != blake2_hash:
                group_id = group_id + 1

            try:
                SearchResult.objects.filter(id=row.id).update(group_id=group_id)
            except Exception as e:
                print("update SearchResult is fault, error:", e)
                return False

            pre_blake2_hash = blake2_hash

        return True

    def update_group_ids_by_file_size(self):

        insertQuery = """
            WITH GroupedData AS (
                SELECT
                    id,
                    full_path,
                    hash_md5,
                    hash_blake2,
                    size,
                    mtime,
                    ctime,
                    extension,
                    created_at,
                    updated_at,
                    DENSE_RANK() OVER (ORDER BY size) AS group_id
                FROM file_file
            ),
            GroupCount AS (
                SELECT
                    group_id,
                    COUNT(*) AS row_count
                FROM GroupedData
                GROUP BY group_id
                HAVING COUNT(*) > 1
            )
            SELECT
                g.group_id,
                g.id,
                g.full_path,
                g.hash_md5,
                g.hash_blake2,
                g.size,
                g.mtime,
                g.ctime,
                g.extension,
                g.created_at,
                g.updated_at
            FROM GroupedData g
            JOIN GroupCount gc ON g.group_id = gc.group_id
            ORDER BY g.group_id;
        """

        try:
            SearchResult.objects.all().delete()
        except Exception as e:
            print("delete SearchResult is fault, error:", e)
            return False

        try:
            data = File.objects.raw(insertQuery)
        except Exception as e:
            print("get File is fault, error:", e)

        for row in data:

            blake2_hash = self.get_blake2(row.full_path)

            search_result_data = {
                "group_id": row.group_id,
                "file_id": row.id,
                "full_path": row.full_path,
                "hash_md5": row.hash_md5,
                "hash_blake2": blake2_hash,
                "size": row.size,
                "mtime": row.mtime,
                "ctime": row.ctime,
                "extension": row.extension,
            }

            serializer = SearchResultSerializer(data=search_result_data)
            is_valid = serializer.is_valid(raise_exception=True)

            if is_valid:

                try:
                    search_result_object = SearchResult(
                        group_id=row.group_id,
                        file_id=row.id,
                        full_path=row.full_path,
                        hash_md5=row.hash_md5,
                        hash_blake2=blake2_hash,
                        size=row.size,
                        mtime=row.mtime,
                        ctime=row.ctime,
                        extension=row.extension,
                    )
                    search_result_object.save()

                except Exception as e:
                    print("update file is fault, error:", e)
                    return False

        return True

    def update_group_ids_by_blake2_hash(self):

        insertQuery = """
                WITH GroupedData AS (
                    SELECT
                        id,
                        file_id,
                        full_path,
                        hash_md5,
                        hash_blake2,
                        size,
                        mtime,
                        ctime,
                        extension,
                        created_at,
                        updated_at,
                        DENSE_RANK() OVER (ORDER BY hash_blake2) AS group_id
                    FROM file_searchresult
                ),
                GroupCount AS (
                    SELECT
                        group_id,
                        COUNT(*) AS row_count
                    FROM GroupedData
                    GROUP BY group_id
                    HAVING COUNT(*) = 1
                )
                SELECT
                    g.id,
                    g.group_id,
                    g.file_id,
                    g.full_path,
                    g.hash_md5,
                    g.hash_blake2,
                    g.size,
                    g.mtime,
                    g.ctime,
                    g.extension,
                    g.created_at,
                    g.updated_at
                FROM GroupedData g
                JOIN GroupCount gc ON g.group_id = gc.group_id
                ORDER BY g.group_id;
            """

        data = SearchResult.objects.raw(insertQuery)

        for row in data:
            try:
                SearchResult.objects.filter(id=row.id).delete()
            except Exception as e:
                print("update file is fault, error:", e)
                return False

        return True

    def save_file_hash(self):

        try:
            search_files = SearchResult.objects.all()
        except Exception as e:
            print("get SearchResult is fault, error:", e)
            return None

        for search_file in search_files:
            if os.path.isfile(search_file.full_path):
                search_file_id = search_file.id
                blake2_hash = self.get_blake2(search_file.full_path)

                try:
                    SearchResult.objects.filter(id=search_file_id).update(
                        hash_blake2=blake2_hash
                    )
                except Exception as e:
                    print("update SearchResult is fault, error:", e)
                    return None

                return blake2_hash

        return None

    def delete_all_data(self):
        try:
            File.objects.all().delete()
        except Exception as e:
            print("delete file is fault, error:", e)
            return False
        return True

    def delete_other_reserve_path_file(self, same_file_record_list, reserve_path):
        for same_file_record in same_file_record_list:
            repeat_file_count = 0
            for file_status in same_file_record:
                file_path = file_status["full_path"]
                file_group_id = file_status["group_id"]
                check_path = PurePath(file_path)

                if check_path.is_relative_to(reserve_path):
                    repeat_file_count += 1

                    if DELETE_REPEAT_FILE:
                        if repeat_file_count > 1:
                            print(file_group_id, "delete file(repeat):", file_path)
                            # os.remove(file_path)
                        else:
                            print(file_group_id, "keep file:", file_path)
                    else:
                        print(file_group_id, "keep file:", file_path)
                else:
                    print(file_group_id, "delete file:", file_path)
                    # os.remove(file_path)

    def selete_fils(self, file_list, reserve_path):
        reserve_path = os.path.normpath(reserve_path)
        same_file_record = []
        find_reserve_path = False
        same_file_group_list = []

        for file_status in file_list:
            same_file_record.append(file_status)

            if len(same_file_record) > 1:
                record_group_id_1 = same_file_record[0]["group_id"]
                file_group_id = file_status["group_id"]

                if record_group_id_1 == file_group_id:
                    file_path = file_status["full_path"]
                    check_path = PurePath(file_path)
                    if check_path.is_relative_to(reserve_path):
                        find_reserve_path = True
                else:
                    if find_reserve_path:
                        same_file_record.pop()
                        same_file_group_list.append(same_file_record)

                        find_reserve_path = False
                    same_file_record = []
                    same_file_record.append(file_status)

        return same_file_group_list
