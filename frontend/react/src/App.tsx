import { BrowserRouter } from "react-router-dom";
import Router from "./router";
import { Toaster } from "react-hot-toast";

function App() {
  return (
    <>
      <BrowserRouter>
        <Router />
        <Toaster position="top-center" reverseOrder={false}/>
      </BrowserRouter>
    </>
  );
}

export default App;
