import React, { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { LogOut, Settings, Send, User, Cog, Trash2, RefreshCw, Menu, ChevronRight } from "lucide-react"
import type { McpService } from "@/types/mcp"
import api from "../../api/api"
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from "@/components/ui/popover"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"

// 로딩 애니메이션용 CSS 스타일 추가
const loadingDotsStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '4px',
};

const dotStyle = {
  width: '8px',
  height: '8px',
  borderRadius: '50%',
  backgroundColor: 'white',
  display: 'inline-block',
  animation: 'dotPulse 1.5s infinite ease-in-out',
};

const dot1Style = {
  ...dotStyle,
  animationDelay: '0s',
};

const dot2Style = {
  ...dotStyle,
  animationDelay: '0.2s',
};

const dot3Style = {
  ...dotStyle,
  animationDelay: '0.4s',
};

// 메시지 타입 정의
interface Message {
  id: string
  content: string
  sender: "user" | "bot"
  timestamp: Date
}

// 저장용 메시지 타입 (timestamp를 문자열로 저장)
interface StoredMessage {
  id: string
  content: string
  sender: "user" | "bot"
  timestamp: string
}

export default function ChatPage() {
  const navigate = useNavigate()
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [services, setServices] = useState<McpService[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedService, setSelectedService] = useState<string | null>(null)
  const [guideModalOpen, setGuideModalOpen] = useState(false);
  const [guideService, setGuideService] = useState<McpService | null>(null);

  // 페이지 로드 시 로컬 스토리지에서 채팅 내역 불러오기
  useEffect(() => {
    // 이미 로드된 경우 중복 로드 방지를 위한 플래그
    let isLoaded = false;
    
    const loadChatHistory = () => {
      // 이미 로드된 경우 중복 실행 방지
      if (isLoaded) return false;
      
      try {
        // MCP 서비스 설정 로드
        const savedServices = localStorage.getItem("mcpServices")
        if (savedServices) {
          setServices(JSON.parse(savedServices))
        }
        
        // 채팅 내역 로드 (다른 키 사용)
        const storedMessages = localStorage.getItem("chatHistory")
        
        if (storedMessages) {
          const parsedMessages: StoredMessage[] = JSON.parse(storedMessages)
          
          if (Array.isArray(parsedMessages) && parsedMessages.length > 0) {
            // 저장된 문자열 timestamp를 Date 객체로 변환
            const restoredMessages: Message[] = parsedMessages.map(msg => ({
              ...msg,
              timestamp: new Date(msg.timestamp)
            }))
            
            setMessages(restoredMessages)
            console.log(`채팅 내역 ${restoredMessages.length}개 로드 완료`)
            isLoaded = true;
            return true
          }
        }
        return false
      } catch (error) {
        console.error("채팅 내역 로드 실패:", error)
        return false
      }
    }
    
    // 채팅 내역 로드 시도
    const historyLoaded = loadChatHistory()
    
    // 로드 실패 또는 내역이 없으면 기본 메시지 표시
    if (!historyLoaded) {
      setMessages([{
        id: "welcome",
        content: "안녕하세요! 무엇을 도와드릴까요?",
        sender: "bot",
        timestamp: new Date()
      }])
    }
    
    // 컴포넌트 언마운트 시 플래그 초기화
    return () => {
      isLoaded = false;
    }
  }, [])  // 빈 의존성 배열 유지
  
  // 메시지 변경 시 로컬 스토리지에 저장 (너무 자주 저장하지 않도록 디바운스 추가)
  useEffect(() => {
    // 메시지가 없으면 저장하지 않음
    if (messages.length === 0) return;
    
    const saveTimeout = setTimeout(() => {
      try {
        // Date 객체를 문자열로 변환하여 저장
        const messagesToStore: StoredMessage[] = messages.map(msg => ({
          ...msg,
          timestamp: msg.timestamp.toISOString() // ISO 문자열로 저장
        }))
        
        // 다른 키를 사용하여 저장
        localStorage.setItem("chatHistory", JSON.stringify(messagesToStore))
        console.log(`채팅 내역 ${messages.length}개 저장 완료`)
      } catch (error) {
        console.error("채팅 내역 저장 실패:", error)
      }
    }, 300);  // 300ms 디바운스
    
    // 클린업 함수
    return () => {
      clearTimeout(saveTimeout);
    }
  }, [messages])

  // 메시지가 추가될 때마다 스크롤 맨 아래로 이동
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    // 사용자 메시지 추가
    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      sender: "user",
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    
    // 로딩 상태 시작
    setIsLoading(true)
    
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
    } finally {
      // 로딩 상태 종료
      setIsLoading(false)
    }
  }

  const handleLogout = async () => {
    try {
      // API 요청 보내기
      await api.post("/api/users/logout")
      
      // 로그아웃 시 스토리지 클리어
      localStorage.removeItem('access_token')
      localStorage.removeItem('mcpServices')
      localStorage.removeItem('chatHistory')
      navigate("/login")
    } catch (error) {
      console.error("로그아웃 중 오류 발생:", error)
      alert("로그아웃에 실패했습니다. 다시 시도해주세요.")
    }
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

  // onKeyDown 이벤트 핸들러 타입 수정
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e as unknown as React.FormEvent)
    }
  }

  // 채팅 내역 초기화 함수
  const clearChatHistory = () => {
    // 초기 환영 메시지만 남기고 모든 메시지 삭제
    const welcomeMessage = {
      id: "welcome",
      content: "안녕하세요! 무엇을 도와드릴까요?",
      sender: "bot" as const,
      timestamp: new Date()
    };
    
    // 메시지 상태 업데이트
    setMessages([welcomeMessage]);
    
    // 로컬 스토리지에서 채팅 내역 삭제
    localStorage.removeItem('chatHistory');
    
    // 콘솔에 로그 출력
    console.log("채팅 내역이 초기화되었습니다.");
  };

  // MCP 서비스 목록 로드
  useEffect(() => {
    const loadServices = async () => {
      try {
        const response = await api.get("/api/mcps/")
        // McpServiceResponse[] → McpService[]로 변환
        const formatted = response.data.map((service: any) => ({
          id: service.public_id,
          name: service.name,
          description: service.description,
          icon: service.mcp_type,
          active: service.active ?? false,
          is_selected: service.is_selected ?? false,
          required_env_vars: (service.required_env_vars || []).map((key: string) => ({ key, value: "" }))
        }))
        setServices(formatted)
      } catch (error) {
        console.error("MCP 서비스 로드 실패:", error)
      }
    }
    loadServices()
  }, [])

  // 서비스 선택 시 모달로 가이드 표시
  const handleServiceSelect = (serviceId: string) => {
    const service = services.find(s => s.id === serviceId)
    if (!service) return
    setGuideService(service)
    setGuideModalOpen(true)
  }

  return (
    <div className="min-h-screen bg-black flex flex-col relative">
      {/* 별 배경 - fixed로 변경하여 스크롤해도 배경이 유지되도록 수정 */}
      <div className="fixed inset-0 z-0">
        <div className="stars"></div>
        <div className="twinkling"></div>
      </div>

      {/* 헤더 - z-index를 높여서 가장 앞에 표시 */}
      <header className="fixed top-0 left-0 right-0 w-full z-50 p-4 border-b border-gray-800 bg-black">
        <div className="w-full flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
              title="사이드바 토글"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <h1 className="text-xl font-bold text-white">여봐라</h1>
          </div>
          <div className="flex space-x-2">
            {/* 대화 내역 삭제 버튼 */}
            <Button
              variant="outline"
              size="icon"
              onClick={clearChatHistory}
              className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
             title="대화 내역 삭제"
            >
              <Trash2 className="h-5 w-5 text-red-400" />
            </Button>
            
            <Popover open={settingsOpen} onOpenChange={setSettingsOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
                  title="환경설정"
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
              title="로그아웃"
            >
              <LogOut className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* 스타일 정의를 위한 style 태그 */}
      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes dotPulse {
            0%, 100% {
              opacity: 0.2;
              transform: scale(0.8);
            }
            50% {
              opacity: 1;
              transform: scale(1);
            }
          }
        `
      }} />

      {/* MCP 서비스 사이드바 */}
      <div className={`fixed left-0 top-16 bottom-0 w-64 bg-gray-900/95 border-r border-gray-800 z-40 transition-transform duration-300 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-4">
          <h2 className="text-lg font-semibold text-white mb-4">채팅 가이드라인</h2>
          <div className="space-y-2">
            {services.map((service) => (
              <div
                key={service.id}
                onClick={() => handleServiceSelect(service.id)}
                className="p-3 rounded-lg cursor-pointer bg-gray-800/50 text-white hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{service.name}</p>
                    <p className="text-xs text-gray-400 mt-1 line-clamp-1">{service.description}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 채팅 영역 - 헤더와 입력창 높이를 고려한 패딩 추가 */}
      <div className={`flex-1 overflow-y-auto p-4 mt-16 mb-24 z-10 relative transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
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
            
            {/* 응답 로딩 중 표시 */}
            {isLoading && (
              <div className="flex justify-start">
                <Card className="max-w-[80%] p-3 bg-gray-800/80 text-white border-gray-700">
                  <div className="flex items-center space-x-2">
                    <div style={loadingDotsStyle}>
                      <span style={dot1Style}></span>
                      <span style={dot2Style}></span>
                      <span style={dot3Style}></span>
                    </div>
                    <p className="ml-2">답변 생성 중...</p>
                  </div>
                </Card>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* 입력 영역 - 하단에 고정 */}
      <div className={`fixed bottom-0 left-0 right-0 pt-4 pb-4 px-8 border-t border-gray-800 bg-black z-40 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
        <div className="container mx-auto max-w-4xl">
          <form onSubmit={handleSendMessage} className="flex space-x-5">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              placeholder="메시지를 입력하세요..."
              className="flex-1 bg-gray-900/60 border-gray-700 text-white min-h-[40px] max-h-[150px] resize-none py-2 px-3"
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <Button
              type="submit"
              className={`bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 self-end h-10 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              disabled={isLoading}
            >
              <Send className="h-5 w-5" />
            </Button>
          </form>
        </div>
      </div>

      {/* 서비스 가이드 모달 */}
      <Dialog open={guideModalOpen} onOpenChange={setGuideModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{guideService?.name}</DialogTitle>
            <DialogDescription>{guideService?.description}</DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            <h3 className="font-semibold mb-2">사용 가능한 명령어</h3>
            <ul className="list-disc list-inside space-y-1">
              {guideService?.commands?.map((cmd: any) => (
                <li key={cmd.name}>
                  <span className="font-medium">{cmd.name}</span>: {cmd.description}
                </li>
              ))}
            </ul>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
