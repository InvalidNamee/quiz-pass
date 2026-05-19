import { ElMessage } from 'element-plus'

export function useToast() {
  function show(message: string, type: 'success' | 'error' | 'info' = 'info') {
    ElMessage({ message, type, duration: 3000 })
  }
  return { show }
}
