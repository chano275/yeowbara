import React, { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { LogOut, Settings, Send, User, Cog, Trash2, RefreshCw, Menu, ChevronRight, MessageCircle, MoreVertical, Edit, Trash, Check, X } from "lucide-react"
import type { McpService } from "@/types/mcp"
import api from "../../api/api"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
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

// 이미 정의된 Message 인터페이스 아래에 추가
interface ChatSession {
  session_id: string;
  session_name: string;
  message_count: number;
}

// 세션 응답 형식 정의
interface SessionResponse {
  sessions: ChatSession[];
}

// 메시지 데이터 형식 정의
interface SessionMessagesResponse {
  messages: {
    id: string;
    content: string;
    sender: "user" | "bot";
    timestamp: string;
  }[];
}

// 메시지 데이터 형식 정의
interface ChatHistoryResponse {
  messages?: {
    id: string;
    content: string;
    sender: "user" | "bot";
    timestamp: string;
  }[];
  history?: Array<{
    user: string;
    assistant: string;
    timestamp?: string;
  }>;
}

// 세션 생성 응답 인터페이스
interface CreateSessionResponse {
  session_id: string;
  session_name: string;
  message_count: number;
}

// 공통으로 사용되는 상수 메시지
const WELCOME_MESSAGE: Message = {
  id: "welcome",
  content: "안녕하세요! 무엇을 도와드릴까요?",
  sender: "bot",
  timestamp: new Date()
};

const ERROR_MESSAGE: (errorContent?: string) => Message = (errorContent = "오류가 발생했습니다.") => ({
  id: `error-${Date.now()}`,
  content: errorContent,
  sender: "bot",
  timestamp: new Date()
});

// 메시지 렌더링을 위한 스타일 추가
const markdownStyles = {
  '& pre': {
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
    padding: '1rem',
    borderRadius: '0.5rem',
    overflowX: 'auto',
  },
  '& code': {
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
    padding: '0.2rem 0.4rem',
    borderRadius: '0.25rem',
  },
  '& p': {
    margin: '0.5rem 0',
  },
  '& ul, & ol': {
    margin: '0.5rem 0',
    paddingLeft: '1.5rem',
  },
  '& blockquote': {
    borderLeft: '4px solid rgba(255, 255, 255, 0.2)',
    margin: '0.5rem 0',
    paddingLeft: '1rem',
    color: 'rgba(255, 255, 255, 0.8)',
  },
  '& table': {
    borderCollapse: 'collapse',
    width: '100%',
    margin: '0.5rem 0',
  },
  '& th, & td': {
    border: '1px solid rgba(255, 255, 255, 0.2)',
    padding: '0.5rem',
  },
  '& th': {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  '& a': {
    color: '#a78bfa',
    textDecoration: 'underline',
  },
  '& a:hover': {
    color: '#c4b5fd',
  },
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
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true)
  const [selectedService, setSelectedService] = useState<string | null>(null)
  const [guideModalOpen, setGuideModalOpen] = useState(false);
  const [guideService, setGuideService] = useState<McpService | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [newSessionName, setNewSessionName] = useState<string>("");

  // 공통 함수: 기본 환영 메시지 설정
  const setWelcomeMessage = () => {
    setMessages([{ ...WELCOME_MESSAGE, timestamp: new Date() }]);
  };

  // 공통 함수: 오류 메시지 설정
  const setErrorMessage = (errorMsg: string) => {
    setMessages([ERROR_MESSAGE(errorMsg)]);
  };

  // 공통 함수: history 배열을 메시지 배열로 변환
  const convertHistoryToMessages = (history: Array<any>): Message[] => {
    if (!history || !Array.isArray(history) || history.length === 0) {
      return [{ ...WELCOME_MESSAGE, timestamp: new Date() }];
    }

    return history.map((item: any, index: number) => {
      // user 메시지와 assistant 메시지 각각 생성
      const userMsg: Message = {
        id: `history-user-${index}`,
        content: item.user || "",
        sender: "user",
        timestamp: new Date(item.timestamp || Date.now() - 1000),
      };
      
      const botMsg: Message = {
        id: `history-bot-${index}`,
        content: item.assistant || "",
        sender: "bot",
        timestamp: new Date(item.timestamp || Date.now()),
      };
      
      return [userMsg, botMsg];
    }).flat();
  };

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
      setWelcomeMessage();
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

  // 로그인 후 채팅 페이지 진입 시 자동으로 세션 생성 및 로드
  useEffect(() => {
    const initializeSession = async () => {
      try {
        // 먼저 세션 목록을 불러옵니다
        await fetchChatHistory();
        
        // localStorage에서 이전에 선택한 세션 ID 확인
        const savedSessionId = localStorage.getItem('selectedSessionId');
        
        // 브라우저 세션에 세션 생성 여부 확인 (세션 스토리지 사용)
        const sessionCreated = sessionStorage.getItem('chat_session_created');
        
        if (savedSessionId) {
          // 저장된 세션 ID가 있으면 해당 세션 선택
          console.log('저장된 세션 ID로 대화 내역 로드:', savedSessionId);
          selectChatHistory(savedSessionId);
        } else if (!sessionCreated) {
          // 새 세션을 생성합니다
          const response = await api.post<CreateSessionResponse>("/api/sessions", {
            session_name: "새 대화"
          });
          
          // 새로 생성된 세션이 반환된 경우 해당 세션으로 이동
          if (response.data && response.data.session_id) {
            // 새 세션 선택
            console.log('선택된 최근 세션:', response.data.session_id);
            selectChatHistory(response.data.session_id);
            console.log("채팅 페이지 진입 시 새 세션 생성됨:", response.data.session_id);
            
            // 브라우저 세션에 세션 생성 여부 저장 (브라우저 닫기 전까지 유지)
            sessionStorage.setItem('chat_session_created', 'true');
          } else {
            setWelcomeMessage();
          }
        } else if (chatHistory.length > 0) {
          // 기존 세션이 있으면 가장 최근 세션 선택
          const latestSession = chatHistory[0]; // 첫 번째 세션이 가장 최근 세션이라고 가정
          if (latestSession && latestSession.session_id) {
            console.log('선택된 최근 세션:', latestSession.session_id);
            selectChatHistory(latestSession.session_id);
            console.log("기존 세션 로드됨:", latestSession.session_id);
          } else {
            setWelcomeMessage();
          }
        } else {
          setWelcomeMessage();
        }
      } catch (error) {
        console.error("세션 초기화 중 오류 발생:", error);
        setWelcomeMessage();
      }
    };
    
    // 페이지 로드 시 기본 메시지 설정
    setWelcomeMessage();
    
    initializeSession();
  }, []); // 컴포넌트 마운트 시 한 번만 실행

  // 채팅 내역 선택 함수
  const selectChatHistory = async (session_id: string) => {
    try {
      setIsLoading(true);
      setSelectedSessionId(session_id);
      
      // 선택한 세션 ID를 localStorage에 저장
      localStorage.setItem('selectedSessionId', session_id);
      
      console.log(`대화내역 불러오기 시작: 세션 ID ${session_id}`);
      
      // 선택한 채팅 내역 로드 (URL 끝의 슬래시 제거 - API 요구사항에 맞춤)
      const response = await api.get<ChatHistoryResponse>(`/api/sessions/${session_id}/history`);
      console.log('API 응답 받음:', response.data);
      
      // 서버에서 history 배열이 있는 경우 (새로운 응답 형식)
      if (response.data && Array.isArray((response.data as any).history)) {
        const history = (response.data as any).history;
        console.log('대화 내역 배열:', history);
        
        // history 배열을 메시지 목록으로 변환
        const newMessages = convertHistoryToMessages(history);
        
        console.log('변환된 메시지 배열:', newMessages);
        // 전체 대화 내역을 새로 설정
        setMessages(newMessages);
      }
      // 기존 응답 형식 처리 (messages 배열이 있는 경우)
      else if (response.data && response.data.messages && Array.isArray(response.data.messages)) {
        // API에서 받아온 메시지를 현재 형식으로 변환
        const formattedMessages = response.data.messages.map((msg) => ({
          id: msg.id,
          content: msg.content,
          sender: msg.sender,
          timestamp: new Date(msg.timestamp)
        }));
        
        console.log(`메시지 ${formattedMessages.length}개 변환 완료`);
        setMessages(formattedMessages);
      } else {
        console.log('메시지가 없거나 배열이 아님, 기본 메시지 표시');
        setWelcomeMessage();
      }
    } catch (error: any) {
      console.error(`채팅 내역 ${session_id} 로드 실패:`, error);
      console.log('상세 오류 정보:', error.response?.status, error.response?.data);
      setErrorMessage("채팅 내역을 불러오는 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    // 세션 ID가 없는 경우 메시지를 보낼 수 없음
    if (!selectedSessionId) {
      alert("선택된 대화방이 없습니다. 새 대화를 시작하거나 기존 대화를 선택해주세요.");
      return;
    }

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
      // 실제 API 호출 - 새로운 엔드포인트 사용
      const response = await api.post(`/api/sessions/${selectedSessionId}/chat`, { message: input })
      console.log('채팅 응답:', response.data);
      
      // 서버에서 history 배열이 있는 경우 (새로운 응답 형식)
      if (response.data && Array.isArray((response.data as any).history)) {
        // 전체 history를 새로운 메시지 목록으로 변환
        const history = (response.data as any).history;
        const newMessages = convertHistoryToMessages(history);
        
        // 전체 대화 내역을 새로 설정
        setMessages(newMessages);
      } 
      // 기존 응답 형식 처리 (fallback)
      else if (response.data && (response.data as any).response) {
        const data = response.data as { response: string };
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: data.response,
          sender: "bot",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, botMessage]);
      }
      else {
        // 응답 형식이 예상과 다를 경우
        console.error('예상하지 못한 응답 형식:', response.data);
        const errorMessage: Message = {
          id: (Date.now() + 2).toString(),
          content: "서버 응답 형식이 올바르지 않습니다.",
          sender: "bot",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
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
      
      // 첫 번째 메시지를 보냈을 때만 세션 목록을 업데이트
      // 환영 메시지(1개) + 사용자 메시지(1개) = 2개
      if (messages.length === 3) {
        console.log("첫 메시지 전송 후 세션 목록 업데이트");
        fetchChatHistory();
      }
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

  // 새로운 채팅 세션 생성 함수
  const createNewSession = async () => {
    try {
      // 먼저 대화가 없는 빈 세션이 있는지 확인
      const emptySession = chatHistory.find(session => session.message_count === 0);
      
      if (emptySession) {
        console.log('빈 세션이 이미 존재합니다. 새 세션을 생성하지 않고 기존 세션을 사용합니다:', emptySession.session_id);
        
        // 기존의 빈 세션 ID만 설정하고 내역은 로드하지 않음
        setSelectedSessionId(emptySession.session_id);
        localStorage.setItem('selectedSessionId', emptySession.session_id);
        
        // 환영 메시지만 표시
        setWelcomeMessage();
        
        return; // 함수 종료
      }
      
      // 빈 세션이 없으면 새 세션 생성
      const response = await api.post<CreateSessionResponse>("/api/sessions", {
        session_name: "새 대화"
      });
      
      // 새로 생성된 세션이 반환된 경우 해당 세션 ID 설정
      if (response.data && response.data.session_id) {
        // 세션 ID만 설정하고 내역은 로드하지 않음
        setSelectedSessionId(response.data.session_id);
        localStorage.setItem('selectedSessionId', response.data.session_id);
        
        // 환영 메시지 표시
        setWelcomeMessage();
      }
      
      // 세션 생성 플래그 재설정하여 다음 페이지 로드 시 다시 새 세션 생성 안되도록 함
      sessionStorage.setItem('chat_session_created', 'true');
    } catch (error) {
      console.error("새 채팅 세션 생성 실패:", error);
    }
  };

  // 채팅 내역 불러오기 함수를 컴포넌트 내부에서 직접 호출할 수 있도록 정의
  const fetchChatHistory = async () => {
    try {
      // API 엔드포인트로 GET 요청
      console.log('세션 목록 불러오기 시작');
      const response = await api.get<SessionResponse>("/api/sessions");
      console.log('세션 목록 응답:', response.data);
      
      if (response.data && response.data.sessions) {
        console.log(`세션 ${response.data.sessions.length}개 불러옴:`, response.data.sessions);
        setChatHistory(response.data.sessions);
      } else {
        console.log('세션이 없음');
        setChatHistory([]);
      }
    } catch (error: any) {
      console.error("채팅 내역 로드 실패:", error);
      console.log('상세 오류 정보:', error.response?.status, error.response?.data);
      setChatHistory([]);
    }
  };

  // 세션 이름 변경 함수
  const renameSession = async (session_id: string, newName: string) => {
    if (!newName.trim()) return;
    
    try {
      // API 호출하여 세션 이름 변경
      await api.put(`/api/sessions/${session_id}`, {
        session_name: newName
      });
      
      // 세션 목록 다시 불러오기
      await fetchChatHistory();
      
      // 편집 모드 종료
      setEditingSessionId(null);
      setNewSessionName("");
    } catch (error) {
      console.error("세션 이름 변경 실패:", error);
      alert("세션 이름 변경에 실패했습니다.");
    }
  };

  // 세션 삭제 함수
  const deleteSession = async (session_id: string) => {
    if (!window.confirm("정말 이 대화를 삭제하시겠습니까?")) return;
    
    try {
      // API 호출하여 세션 삭제
      await api.delete(`/api/sessions/${session_id}`);
      
      // 세션 목록 다시 불러오기
      await fetchChatHistory();
      
      // 삭제한 세션이 현재 선택된 세션이면 선택 해제 및 localStorage에서 제거
      if (selectedSessionId === session_id) {
        setSelectedSessionId(null);
        localStorage.removeItem('selectedSessionId');
        setWelcomeMessage();
      }
    } catch (error) {
      console.error("세션 삭제 실패:", error);
      alert("세션 삭제에 실패했습니다.");
    }
  };

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
            {!leftSidebarOpen && (
              <Button
                variant="outline"
                size="icon"
                onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
                className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
                title="채팅 내역"
              >
                <MessageCircle className="h-5 w-5" />
              </Button>
            )}
            <h1 className={`text-xl font-bold text-white transition-transform duration-300 ease-in-out ${leftSidebarOpen ? 'translate-x-64' : 'translate-x-0'}`}>여봐라</h1>
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
            <Button
              variant="outline"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
              title="채팅 가이드라인"
            >
              <Menu className="h-5 w-5" />
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

          .markdown-content pre {
            background-color: rgba(0, 0, 0, 0.2);
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
          }

          .markdown-content code {
            background-color: rgba(0, 0, 0, 0.2);
            padding: 0.2rem 0.4rem;
            border-radius: 0.25rem;
          }

          .markdown-content p {
            margin: 0.5rem 0;
          }

          .markdown-content ul,
          .markdown-content ol {
            margin: 0.5rem 0;
            padding-left: 1.5rem;
          }

          .markdown-content blockquote {
            border-left: 4px solid rgba(255, 255, 255, 0.2);
            margin: 0.5rem 0;
            padding-left: 1rem;
            color: rgba(255, 255, 255, 0.8);
          }

          .markdown-content table {
            border-collapse: collapse;
            width: 100%;
            margin: 0.5rem 0;
          }

          .markdown-content th,
          .markdown-content td {
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 0.5rem;
          }

          .markdown-content th {
            background-color: rgba(255, 255, 255, 0.1);
          }

          .markdown-content a {
            color: #a78bfa;
            text-decoration: underline;
          }

          .markdown-content a:hover {
            color: #c4b5fd;
          }
        `
      }} />

      {/* 왼쪽 사이드바 - 채팅 내역 */}
      <div className={`fixed left-0 top-0 bottom-0 w-64 bg-gray-900/90 border-r border-gray-800 z-[51] transition-transform duration-300 ${leftSidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="relative p-4 h-full flex flex-col pt-20">
          {/* 상단바와 동일한 위치에 배치된 버튼 */}
          <div className="absolute top-4 left-4">
            <Button
              variant="outline"
              size="icon"
              onClick={() => setLeftSidebarOpen(false)}
              className="border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white"
              title="채팅 내역"
            >
              <MessageCircle className="h-5 w-5" />
            </Button>
          </div>
          <h2 className="text-lg font-semibold text-white mb-4">채팅 내역</h2>
          <div className="space-y-2 overflow-y-auto flex-1">
            {/* 새 채팅 버튼 */}
            <Button
              variant="outline"
              className="w-full bg-gradient-to-r from-indigo-500/20 to-purple-600/20 border-gray-700 hover:bg-gray-800 mb-2"
              onClick={() => {
                createNewSession();
              }}
            >
              <span className="text-white">새 채팅</span>
            </Button>
            
            {/* 채팅 내역 목록 */}
            {chatHistory.length > 0 ? (
              chatHistory
                .map((session) => (
                <div
                  key={session.session_id}
                  className={`p-3 rounded-lg cursor-pointer text-white hover:bg-gray-700 transition-colors border ${
                    selectedSessionId === session.session_id 
                      ? "bg-gray-700/90 border-purple-500" 
                      : "bg-gray-800/80 border-gray-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div 
                      className="flex-1"
                      onClick={() => {
                        selectChatHistory(session.session_id);
                      }}
                    >
                      {editingSessionId === session.session_id ? (
                        <div className="flex items-center space-x-2">
                          <input
                            type="text"
                            value={newSessionName}
                            onChange={(e) => setNewSessionName(e.target.value)}
                            className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-white"
                            onClick={(e) => e.stopPropagation()}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault();
                                renameSession(session.session_id, newSessionName);
                              }
                            }}
                            autoFocus
                          />
                          <button 
                            onClick={(e) => {
                              e.stopPropagation();
                              renameSession(session.session_id, newSessionName);
                            }}
                            className="text-green-500 hover:text-green-400"
                          >
                            <Check className="h-4 w-4" />
                          </button>
                          <button 
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingSessionId(null);
                            }}
                            className="text-red-500 hover:text-red-400"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <p className="text-sm font-medium">{session.session_name}</p>
                          <p className="text-xs text-gray-400 mt-1">
                            메시지 {session.message_count}개
                          </p>
                        </>
                      )}
                    </div>
                    <div className="flex items-center">
                      <Popover>
                        <PopoverTrigger asChild>
                          <button
                            onClick={(e) => e.stopPropagation()}
                            className="p-1 hover:bg-gray-600 rounded-full focus:outline-none"
                          >
                            <MoreVertical className="h-4 w-4 text-gray-400" />
                          </button>
                        </PopoverTrigger>
                        <PopoverContent className="w-40 p-0 bg-gray-800 border-gray-700 z-[100]">
                          <div className="flex flex-col text-sm">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditingSessionId(session.session_id);
                                setNewSessionName(session.session_name);
                              }}
                              className="flex items-center gap-2 p-2 hover:bg-gray-700 text-left text-white"
                            >
                              <Edit className="h-4 w-4 text-blue-400" />
                              <span>이름 변경</span>
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteSession(session.session_id);
                              }}
                              className="flex items-center gap-2 p-2 hover:bg-gray-700 text-left text-white"
                            >
                              <Trash className="h-4 w-4 text-red-400" />
                              <span>삭제</span>
                            </button>
                          </div>
                        </PopoverContent>
                      </Popover>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>채팅 내역이 없습니다.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* MCP 서비스 사이드바 */}
      <div className={`fixed right-0 top-16 bottom-0 w-64 bg-gray-900/90 border-l border-gray-800 z-40 transition-transform duration-300 ${sidebarOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="p-4 h-full flex flex-col">
          <h2 className="text-lg font-semibold text-white mb-4">채팅 가이드라인</h2>
          <div className="space-y-2 overflow-y-auto flex-1">
            {services.map((service) => (
              <div
                key={service.id}
                onClick={() => {
                  handleServiceSelect(service.id);
                  setLeftSidebarOpen(false);
                }}
                className="p-3 rounded-lg cursor-pointer bg-gray-800/80 text-white hover:bg-gray-700 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{service.name}</p>
                    <p className="text-xs text-gray-400 mt-1 line-clamp-1">{service.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 채팅 영역 - 헤더와 입력창 높이를 고려한 패딩 추가 */}
      <div className={`flex-1 overflow-y-auto p-4 mt-16 mb-24 z-10 relative transition-all duration-300 ${leftSidebarOpen ? 'ml-64' : 'ml-0'} ${sidebarOpen ? 'mr-64' : 'mr-0'}`}>
        <div className="container mx-auto max-w-4xl">
          <div className="space-y-4">
            {messages.length > 0 ? (
              messages.map((message) => (
                <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
                  <Card
                    className={`max-w-[80%] p-3 ${
                      message.sender === "user"
                        ? "bg-purple-600 text-white border-purple-700"
                        : "bg-gray-800/80 text-white border-gray-700"
                    }`}
                  >
                    <div className="markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                    <p className="text-xs opacity-70 mt-1">
                      {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </Card>
                </div>
              ))
            ) : (
              <div className="flex justify-start">
                <Card className="max-w-[80%] p-3 bg-gray-800/80 text-white border-gray-700">
                  <div className="markdown-content">
                    <p>안녕하세요! 무엇을 도와드릴까요?</p>
                  </div>
                  <p className="text-xs opacity-70 mt-1">
                    {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </Card>
              </div>
            )}
            
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
      <div className={`fixed bottom-0 left-0 right-0 pt-4 pb-4 px-8 border-t border-gray-800 bg-black z-40 transition-all duration-300 ${leftSidebarOpen ? 'ml-64' : 'ml-0'} ${sidebarOpen ? 'mr-64' : 'mr-0'}`}>
        <div className="container mx-auto max-w-4xl">
          <form onSubmit={handleSendMessage} className="flex space-x-5">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              placeholder="메시지를 입력하세요..."
              className="flex-1 bg-gray-900/60 border-gray-700 text-white min-h-[40px] max-h-[150px] resize-none py-2 px-3"
              onKeyDown={handleKeyDown}
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
