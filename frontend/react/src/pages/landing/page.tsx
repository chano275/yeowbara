import { Button } from "@/components/ui/button"
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react"
import "@/styles/globals.css";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen bg-black overflow-hidden flex flex-col items-center justify-center">
      {/* 별 배경 */}
      <div className="absolute inset-0 z-0">
        <div className="stars"></div>
        <div className="twinkling"></div>
      </div>

      {/* 행성 이미지 */}
      <div className="absolute bottom-[-100px] right-[-100px] w-[500px] h-[500px] rounded-full bg-purple-900/30 blur-3xl"></div>
      <div className="absolute top-[-50px] left-[-50px] w-[300px] h-[300px] rounded-full bg-blue-900/20 blur-3xl"></div>

      {/* 콘텐츠 */}
      <div className="z-10 text-center px-4 sm:px-6 lg:px-8">
        <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold text-white mb-6 tracking-tight">
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-blue-500 to-indigo-600">
            우주 탐험을 시작하세요
          </span>
        </h1>
        <p className="text-xl sm:text-2xl text-gray-300 mb-10 max-w-2xl mx-auto">
          MCP를 통한 무한한 가능성이 펼쳐지는 공간에서 당신만의 여정을 시작하세요
        </p>
        <Link to="/login">
          <Button
            size="lg"
            className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:from-indigo-600 hover:via-purple-600 hover:to-pink-600 text-white font-medium px-8 py-6 rounded-full text-lg"
          >
            <Sparkles className="mr-2 h-5 w-5" />
            서비스 시작하기
          </Button>
        </Link>
      </div>

      {/* 우주선 애니메이션 */}
      {/* <div className="absolute z-10 w-20 h-20 animate-float"> */}
      {/* <div className="absolute z-10 w-20 h-20 animate-float" style={{ top: '20px' }}> */}
      <div className="absolute z-10 w-20 h-20 animate-float top-65">
        <div className="relative w-10 h-16 bg-gray-200 rounded-t-full transform -rotate-45 left-5 top-2">
          <div className="absolute bottom-0 left-0 w-10 h-4 bg-red-500 rounded-b-lg"></div>
          <div className="absolute -right-2 bottom-4 w-4 h-8 bg-gray-300 rounded-tr-lg"></div>
        </div>
      </div>
    </div>
  );
};
