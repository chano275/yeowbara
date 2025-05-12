import React, { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { LogOut, Settings, Send, User, Cog } from "lucide-react"
import type { McpService } from "@/types/mcp"
import api from "../../api/api"
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from "@/components/ui/popover"
import { Textarea } from "@/components/ui/textarea"

// 메시지 타입 정의
interface Message {
  id: string
  content: string
  sender: "user" | "bot"
  timestamp: Date
}

export default function ChatPage() {
  const navigate = useNavigate()
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content: "안녕하세요! 무엇을 도와드릴까요?",
      sender: "bot",
      timestamp: new Date(),
    },
  ])
  const [services, setServices] = useState<McpService[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  // 로컬 스토리지에서 MCP 서비스 설정 불러오기
  useEffect(() => {
    const savedServices = localStorage.getItem("mcpServices")
    if (savedServices) {
      setServices(JSON.parse(savedServices))
    }
  }, [])

  // 메시지가 추가될 때마다 스크롤 맨 아래로 이동
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    // 사용자 메시지 추가
    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      sender: "user",
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInput("")

    try {
      // 실제 API 호출
      const response = await api.post("/api/chat", { message: input })
      const data = response.data as { response: string }
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response, // 서버 응답에 맞게 수정
        sender: "bot",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, botMessage])
    } catch (error: any) {
      // 서버에서 반환한 에러 메시지 추출
      let errorMsg = "서버와의 통신에 실패했습니다."
      if (error?.response?.data) {
        if (typeof error.response.data === 'string') {
          errorMsg = error.response.data
        } else if (error.response.data.detail) {
          if (Array.isArray(error.response.data.detail)) {
            errorMsg = error.response.data.detail.map((d: any) => d.msg).join(' ')
          } else if (typeof error.response.data.detail === 'string') {
            errorMsg = error.response.data.detail
          }
        }
      }
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        content: errorMsg,
        sender: "bot",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    }
  }

  const handleLogout = () => {
    // 실제 구현에서는 로그아웃 로직 추가
    localStorage.removeItem('access_token')
    localStorage.removeItem('mcpServices')
    navigate("/login")
  }

  const handleNavigateToMyPage = () => {
    navigate("/mypage")
    setSettingsOpen(false)
  }

  const handleNavigateToMcpSetup = () => {
    navigate("/mcp-setup")
    setSettingsOpen(false)
  }

  // 텍스트 입력 시 높이 자동 조절을 위한 ref
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // 텍스트 입력 시 높이 자동 조절
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      const newHeight = Math.min(textarea.scrollHeight, 150) // 최대 높이 150px로 제한
      textarea.style.height = `${newHeight}px`
    }
  }

  // 입력 변경 시 높이 조절 및 상태 업데이트
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    adjustTextareaHeight()
  }

  // 초기 렌더링 시 높이 조절
  useEffect(() => {
    adjustTextareaHeight()
  }, [])

  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* 별 배경 */}
      <div className="absolute inset-0 z-0">
        <div className="stars"></div>
        <div className="twinkling"></div>
      </div>

      {/* 헤더 */}
      <header className="z-10 p-4 border-b border-gray-800 bg-black/60 backdrop-blur-lg">
        <div className="container mx-auto flex justify-between items-center">
          <h1 className="text-xl font-bold text-white">여봐라</h1>
          <div className="flex space-x-2">
            <Popover open={settingsOpen} onOpenChange={setSettingsOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
                >
                  <Settings className="h-5 w-5" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-56 bg-gray-900 border-gray-700 text-white p-0" align="end">
                <div className="flex flex-col">
                  <Button 
                    onClick={handleNavigateToMyPage}
                    variant="ghost"
                    className="flex items-center justify-start gap-2 py-2 px-3 hover:bg-gray-800 rounded-none"
                  >
                    <User className="h-5 w-5 text-purple-400" />
                    <span>마이페이지</span>
                  </Button>
                  <Button 
                    onClick={handleNavigateToMcpSetup}
                    variant="ghost"
                    className="flex items-center justify-start gap-2 py-2 px-3 hover:bg-gray-800 rounded-none"
                  >
                    <Cog className="h-5 w-5 text-purple-400" />
                    <span>MCP 설정</span>
                  </Button>
                </div>
              </PopoverContent>
            </Popover>
            <Button
              variant="outline"
              size="icon"
              onClick={handleLogout}
              className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
            >
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* 채팅 영역 */}
      <div className="flex-1 overflow-y-auto p-4 z-10">
        <div className="container mx-auto max-w-4xl">
          <div className="space-y-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
                <Card
                  className={`max-w-[80%] p-3 ${
                    message.sender === "user"
                      ? "bg-purple-600 text-white border-purple-700"
                      : "bg-gray-800/80 text-white border-gray-700"
                  }`}
                >
                  <p>{message.content}</p>
                  <p className="text-xs opacity-70 mt-1">
                    {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </Card>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* 입력 영역 */}
      <div className="pt-6 pb-6 px-8 border-t border-gray-800 bg-black/60 backdrop-blur-lg z-10">
        <div className="container mx-auto max-w-4xl">
          <form onSubmit={handleSendMessage} className="flex space-x-5">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              placeholder="메시지를 입력하세요..."
              className="flex-1 bg-gray-900/60 border-gray-700 text-white min-h-[40px] max-h-[150px] resize-none py-2 px-3"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSendMessage(e)
                }
              }}
            />
            <Button
              type="submit"
              className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 self-end h-10"
            >
              <Send className="h-5 w-5" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
