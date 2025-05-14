"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Link, useNavigate } from "react-router-dom"
import { Rocket, Loader2 } from "lucide-react"
import api from "../../api/api"
import axios from 'axios'

interface LoginResponse {
  access_token: string;
  [key: string]: any;
}

export default function LoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      // const response = await axios.post(
      //   'https://k12b107.p.ssafy.io/api/users/login',
      const response = await api.post<LoginResponse>(
        '/api/users/login',
        new URLSearchParams({
          username,
          password,
        }),
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        }
      );
      
      if (response.data && response.data.access_token) {
        localStorage.setItem('access_token', response.data.access_token)
        navigate("/chat")
      } else {
        alert("로그인에 실패했습니다. 토큰 발급에 실패했습니다.")
        setIsLoading(false)
      }
    } catch (error) {
      console.error('Login failed:', error)
      alert("로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.")
      setIsLoading(false)
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
            <Rocket className="h-12 w-12 text-purple-500" />
          </div>
          <CardTitle className="text-2xl font-bold text-white">로그인</CardTitle>
          <CardDescription className="text-gray-400">계정에 로그인하여 우주 여행을 시작하세요</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium text-gray-300">
                아이디
              </label>
              <Input
                id="username"
                placeholder="아이디를 입력하세요"
                value={username}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUsername(e.target.value)}
                className="bg-gray-900/60 border-gray-700 text-white"
                required
                disabled={isLoading}
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
                disabled={isLoading}
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  로그인 중...
                </>
              ) : (
                '로그인'
              )}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center">
          <p className="text-sm text-gray-400">
            계정이 없으신가요?{" "}
            <Link to="/signup" className="text-purple-400 hover:text-purple-300 font-medium">
              회원가입
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
