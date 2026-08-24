import asyncio

from minio import Minio
from minio.deleteobjects import DeleteObject, DeleteError

from app.client.minio_client import init_minio_client
from app.config.minio_config import minio_config
from app.exception.oper_exception_hook import oper_exception_hook


class MinioOper:
    def __init__(self, minio_client: Minio):
        self.client: Minio = minio_client

    # 上传image到minio
    @oper_exception_hook("minio")
    async def upload(self,object_name:str,file_path:str,bucket_name:str = minio_config.bucket_name):
        def _upload():
            self.client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type="image/jpeg"
            )

        await asyncio.to_thread(_upload)

    # 根据文件夹名，获取文件
    @oper_exception_hook("minio")
    async def get_file_by_dir(self,dir_name:str,bucket_name:str = minio_config.bucket_name):
        def _get_file_by_dir():
            files = self.client.list_objects(
                bucket_name=bucket_name,
                prefix=dir_name,
                recursive=True
            )
            return files
        return await asyncio.to_thread(_get_file_by_dir)

    # 删除文件夹内的文件
    @oper_exception_hook("minio")
    async def remove_dir(self, dir_name: str, bucket_name: str = minio_config.bucket_name):
        files_to_delete = await self.get_file_by_dir(dir_name)
        files_to_delete = list(files_to_delete)
        if not files_to_delete:
            return

        def _remove_dir():
            # 构造删除对象列表
            delete_list = [DeleteObject(obj.object_name) for obj in files_to_delete]
            errors = self.client.remove_objects(bucket_name, delete_list)
            errors = list(errors)
            if errors:
                failed = [f"{e.object_name}: {e.exception}" for e in errors]
                raise RuntimeError(f"删除 minio 对象部分失败: {"; ".join(failed)}")

        await asyncio.to_thread(_remove_dir)