"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Link, useNavigate } from "react-router-dom"
import { UserPlus } from "lucide-react"
import api from "../../api/api"

export default function SignupPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [username, setUsername] = useState("")
  const [errorMessage, setErrorMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage("")
    setLoading(true)
    try {
      await api.post('/api/users/signup', { 
        username: username, 
        email: email, 
        password: password 
      })
      navigate("/login")
    } catch (error: any) {
      console.error('Signup failed:', error)
      if (error.response) {
        const errorDetail = error.response.data?.detail;
        if (errorDetail) {
          if (Array.isArray(errorDetail)) {
            setErrorMessage(errorDetail.map((d: any) => d.msg).join('\n'));
          } else {
            setErrorMessage(errorDetail);
          }
        } else {
          setErrorMessage('회원가입에 실패했습니다. 입력 정보를 확인하거나 다시 시도해주세요.');
        }
      } else if (error.request) {
        setErrorMessage('서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.');
      } else {
        setErrorMessage('회원가입 요청 중 오류가 발생했습니다.');
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      {/* 별 배경 */}
      <div className="absolute inset-0 z-0">
        <div className="stars"></div>
        <div className="twinkling"></div>
      </div>

      <Card className="w-full max-w-md bg-black/60 border border-gray-800 backdrop-blur-lg">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-2">
            <UserPlus className="h-12 w-12 text-purple-500" />
          </div>
          <CardTitle className="text-2xl font-bold text-white">회원가입</CardTitle>
          <CardDescription className="text-gray-400">새로운 계정을 만들어 우주 여행을 시작하세요</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSignup} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-gray-300">
                이메일
              </label>
              <Input
                id="email"
                placeholder="이메일을 입력하세요"
                value={email}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                className="bg-gray-900/60 border-gray-700 text-white"
                required
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-gray-300">
                비밀번호
              </label>
              <Input
                id="password"
                type="password"
                placeholder="비밀번호를 입력하세요"
                value={password}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                className="bg-gray-900/60 border-gray-700 text-white"
                required
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium text-gray-300">
                이름
              </label>
              <Input
                id="username"
                placeholder="이름을 입력하세요"
                value={username}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUsername(e.target.value)}
                className="bg-gray-900/60 border-gray-700 text-white"
                required
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700"
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin h-5 w-5 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
                  </svg>
                  회원가입 중...
                </span>
              ) : (
                '가입하기'
              )}
            </Button>
            {errorMessage && (
              <div className="mt-2 text-sm text-red-500 whitespace-pre-line text-center">
                {errorMessage}
              </div>
            )}
          </form>
        </CardContent>
        <CardFooter className="flex justify-center">
          <p className="text-sm text-gray-400">
            이미 계정이 있으신가요?{" "}
            <Link to="/login" className="text-purple-400 hover:text-purple-300 font-medium">
              로그인
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
