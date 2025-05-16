import { Routes, Route, Navigate } from "react-router-dom";
import LandingPage from "../pages/landing/page";
import HelloWorld from "../pages/HelloWorld/page";
import LoginPage from "../pages/login/page";
import SignupPage from "../pages/signup/page";
import ChatPage from "../pages/chat/page";
import McpSetupPage from "../pages/mcp-setup/page";
import MyPage from "../pages/mypage/page";

// 토큰 체크를 위한 PrivateRoute 컴포넌트
const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const token = localStorage.getItem('access_token');
  
  if (token) {
    return <Navigate to="/chat" replace />;
  }
  
  return <>{children}</>;
};

const Router = () => {
  return (
    <Routes>
      <Route path="/" element={
        <PrivateRoute>
          <LandingPage />
        </PrivateRoute>
      } />
      <Route path="/helloworld" element={<HelloWorld />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/chat" element={<ChatPage />} />
      <Route path="/mcp-setup" element={<McpSetupPage />} />
      <Route path="/mypage" element={<MyPage />} />
    </Routes>
  );
};

export default Router;
