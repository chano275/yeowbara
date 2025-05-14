import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useNavigate } from "react-router-dom"
import { User, AlertTriangle, ArrowLeft, CheckCircle2, XCircle } from "lucide-react"
import api from "../../api/api"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

export default function MyPage() {
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [passwordsMatch, setPasswordsMatch] = useState(true)
  const [passwordError, setPasswordError] = useState("")

  // 비밀번호 일치 여부 확인
  const checkPasswordMatch = () => {
    if (confirmPassword === "") {
      setPasswordsMatch(true)
      setPasswordError("")
      return
    }
    
    if (newPassword === confirmPassword) {
      setPasswordsMatch(true)
      setPasswordError("")
    } else {
      setPasswordsMatch(false)
      setPasswordError("비밀번호가 일치하지 않습니다")
    }
  }

  // 비밀번호 변경 시 일치 여부 확인
  const handleNewPasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNewPassword(e.target.value)
    if (confirmPassword) {
      // 확인 비밀번호가 이미 입력된 상태라면 일치 여부 즉시 확인
      setTimeout(() => {
        if (e.target.value === confirmPassword) {
          setPasswordsMatch(true)
          setPasswordError("")
        } else {
          setPasswordsMatch(false)
          setPasswordError("비밀번호가 일치하지 않습니다")
        }
      }, 300)
    }
  }

  // 확인 비밀번호 변경 시 일치 여부 확인
  const handleConfirmPasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setConfirmPassword(e.target.value)
    setTimeout(() => {
      if (newPassword === e.target.value) {
        setPasswordsMatch(true)
        setPasswordError("")
      } else {
        setPasswordsMatch(false)
        setPasswordError("비밀번호가 일치하지 않습니다")
      }
    }, 300)
  }

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // 비밀번호 일치 여부 확인
    if (newPassword !== confirmPassword) {
      setPasswordsMatch(false)
      setPasswordError("비밀번호가 일치하지 않습니다")
      return
    }
    
    // 비밀번호가 비어있는지 확인
    if (!currentPassword) {
      setPasswordError("현재 비밀번호를 입력해주세요")
      return
    }
    
    if (!newPassword) {
      setPasswordError("새 비밀번호를 입력해주세요")
      return
    }
    
    // 로딩 상태 표시 등을 위한 상태 추가
    setPasswordError("")
    
    try {
      // API 호출 (실제 엔드포인트에 맞게 조정)
      const response = await api.put('/users/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      })
      
      console.log("비밀번호 변경 성공:", response)
      
      // 성공 메시지 표시
      alert("비밀번호가 성공적으로 변경되었습니다")
      
      // 입력 필드 초기화
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      setPasswordError("")
    } catch (error: any) {
      console.error('Profile update failed:', error)
      
      // 서버 응답에 따른 오류 메시지 처리
      if (error.response) {
        // 백엔드에서 오는 모든 에러를 detail 필드에서 추출
        const errorDetail = error.response.data?.detail
        
        if (errorDetail) {
          console.log("에러 상세 정보:", errorDetail)
          
          // detail을 직접 표시
          setPasswordError(errorDetail)
        } else {
          // detail이 없는 경우의 처리
          setPasswordError("요청 처리 중 오류가 발생했습니다")
        }
      } else if (error.request) {
        // 요청은 전송되었으나 응답을 받지 못한 경우
        setPasswordError("서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요")
      } else {
        // 요청 전송 과정에서 오류가 발생한 경우
        setPasswordError("요청 처리 중 오류가 발생했습니다")
      }
    }
  }

  const handleDeleteAccount = async () => {
    try {
      await api.delete('/users/me')
      localStorage.removeItem('access_token')
      navigate("/")
    } catch (error) {
      console.error('Account deletion failed:', error)
      // 에러 처리 로직 추가
    }
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      {/* 별 배경 */}
      <div className="absolute inset-0 z-0">
        <div className="stars"></div>
        <div className="twinkling"></div>
      </div>

      {/* 채팅으로 돌아가기 버튼 */}
      <Button 
        variant="ghost" 
        className="absolute top-4 left-4 text-white hover:bg-gray-800 z-10"
        onClick={() => navigate("/chat")}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        채팅으로 돌아가기
      </Button>

      <Card className="w-full max-w-md bg-black/60 border border-gray-800 backdrop-blur-lg">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-2">
            <User className="h-12 w-12 text-purple-500" />
          </div>
          <CardTitle className="text-2xl font-bold text-white">마이페이지</CardTitle>
          <CardDescription className="text-gray-400">회원 정보를 관리할 수 있습니다</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUpdateProfile} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="currentPassword" className="text-sm font-medium text-gray-300">
                현재 비밀번호
              </label>
              <Input
                id="currentPassword"
                type="password"
                placeholder="현재 비밀번호를 입력하세요"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="bg-gray-900/60 border-gray-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="newPassword" className="text-sm font-medium text-gray-300">
                새 비밀번호
              </label>
              <Input
                id="newPassword"
                type="password"
                placeholder="새 비밀번호를 입력하세요"
                value={newPassword}
                onChange={handleNewPasswordChange}
                className="bg-gray-900/60 border-gray-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-medium text-gray-300">
                새 비밀번호 확인
              </label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="새 비밀번호를 다시 입력하세요"
                  value={confirmPassword}
                  onChange={handleConfirmPasswordChange}
                  className={`bg-gray-900/60 border-gray-700 text-white ${confirmPassword && !passwordsMatch ? 'border-red-500' : confirmPassword ? 'border-green-500' : ''}`}
                />
                {confirmPassword && (
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                    {passwordsMatch ? (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                )}
              </div>
              {passwordError && (
                <p className="text-sm text-red-500 mt-1">{passwordError}</p>
              )}
            </div>
            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700"
            >
              정보 수정
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-700">
            <Dialog>
              <DialogTrigger asChild>
                <Button
                  variant="destructive"
                  className="w-full bg-red-600 hover:bg-red-700"
                >
                  <AlertTriangle className="mr-2 h-4 w-4" />
                  회원 탈퇴
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-gray-900 text-white border-gray-700">
                <DialogHeader>
                  <DialogTitle>회원 탈퇴</DialogTitle>
                  <DialogDescription className="text-gray-400">
                    정말로 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button
                    variant="destructive"
                    onClick={handleDeleteAccount}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    탈퇴하기
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
