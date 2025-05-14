// 서비스 아이콘 컴포넌트
export default function ServiceIcon({ name, active, className = "h-8 w-8" }: { name: string; active: boolean; className?: string }) {
  const color = active ? "text-white" : "text-gray-500"

  switch (name) {
    case "github":
      return (
        <svg
          className={`${className} ${color}`}
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
          <path d="M9 18c-4.51 2-5-2-7-2" />
        </svg>
      )
    case "jira":
      return (
        <svg
          className={`${className} ${color}`}
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m12 8.5 4 4-4 4-4-4 4-4Z" />
          <path d="M17.5 15.5 15 18" />
          <path d="m12 3 9 9-9 9-9-9 9-9Z" />
        </svg>
      )
    case "notion":
      return (
        <svg
          className={`${className} ${color}`}
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 6h16" />
          <path d="M4 12h16" />
          <path d="M4 18h12" />
        </svg>
      )
    case "naver":
      return (
        <svg
          className={`${className} ${color}`}
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M9 9v6" />
          <path d="M15 9v6" />
          <path d="M9 9h6" />
          <path d="M9 15h6" />
          <rect width="18" height="18" x="3" y="3" rx="2" />
        </svg>
      )
    case "google":
      return (
        <svg
          className={`${className} ${color}`}
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v8" />
          <path d="M8 12h8" />
        </svg>
      )
    case "map":
      return (
        <svg
          className={`${className} ${color}`}
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
          <line x1="9" x2="9" y1="3" y2="18" />
          <line x1="15" x2="15" y1="6" y2="21" />
        </svg>
      )
    default:
      return (
        <svg
          className={`${className} ${color}`}
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect width="18" height="18" x="3" y="3" rx="2" />
          <path d="M12 8v8" />
          <path d="M8 12h8" />
        </svg>
      )
  }
}