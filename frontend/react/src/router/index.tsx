import { Routes, Route } from "react-router-dom";
import LandingPage from "../pages/landing/page";
import HelloWorld from "../pages/HelloWorld/page";
import LoginPage from "../pages/login/page";
import SignupPage from "../pages/signup/page";
import ChatPage from "../pages/chat/page";


const Router = () => {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/helloworld" element={<HelloWorld />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/chat" element={<ChatPage />} />
    </Routes>
  );
};

export default Router;
