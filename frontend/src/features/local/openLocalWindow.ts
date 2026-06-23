import { openUtilityWindow } from '../utility-windows/utilityWindow'

export function openLocalPracticeSetupWindow(payload: { localBankId: number; title?: string }) {
  return openUtilityWindow(
    'local-practice-setup',
    payload,
    { title: '开始本地练习', width: 460, height: 330, labelSeed: `bank-${payload.localBankId}` },
  )
}

export function openLocalDownloadWindow(payload: { remoteBankId: number; title?: string; alreadyDownloaded?: boolean }) {
  return openUtilityWindow(
    'local-download',
    payload,
    {
      title: payload.alreadyDownloaded ? '更新本地副本' : '下载到本机',
      width: 460,
      height: 310,
      labelSeed: `bank-${payload.remoteBankId}`,
    },
  )
}
