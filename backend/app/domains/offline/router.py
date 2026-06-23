from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domains.offline.schemas import BankDownloadPackage, OfflinePracticeSyncRequest, OfflinePracticeSyncResult
from app.domains.offline.services import BankDownloadPackageService, OfflinePracticeSyncService
from app.models.user import User

router = APIRouter()


@router.get("/banks/{bank_id}/download-package", response_model=BankDownloadPackage)
def download_bank_package(bank_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return BankDownloadPackageService(db).build_package(bank_id, current_user)


@router.post("/offline/practice-sync", response_model=OfflinePracticeSyncResult)
def sync_offline_practice(payload: OfflinePracticeSyncRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return OfflinePracticeSyncService(db).sync(payload, current_user)
