import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { GoogleOAuthProvider } from '@react-oauth/google';
import './styles.css';
import reportWebVitals from './reportWebVitals';
import Login from './pages/Login';
import PageNotFound from './pages/404Page';
import Pools from './pages/Pools';
import { CookiesProvider } from 'react-cookie';
import Navbar from './pages/Navbar';

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/">
          <Route index element={<Login />} />
          <Route path="pools" element={<Pools />} />
          <Route path="*" element={<PageNotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId='62141920981-5eaok6b8edq4pol0e6ncden3cl5caivh.apps.googleusercontent.com'>
      <CookiesProvider>
        <App />
      </CookiesProvider>
    </GoogleOAuthProvider>

  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
