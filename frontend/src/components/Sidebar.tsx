import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/inbox", label: "Inbox" },
  { to: "/bulk", label: "Bulk Processing" },
  { to: "/analytics", label: "Analytics" },
  { to: "/accounts", label: "Email Accounts" },
];

export default function Sidebar() {
  const { email, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="w-[232px] min-w-[232px] bg-surface border-r border-borderSoft flex flex-col p-3.5 h-screen sticky top-0">
      <div className="flex items-center gap-2.5 px-2 pb-6 pt-1">
        <div className="w-[30px] h-[30px] rounded-[9px] bg-gradient-to-br from-accent to-[#8b8ef7] flex items-center justify-center font-display font-bold text-[15px] text-white">
          R
        </div>
        <div>
          <div className="font-display font-semibold text-[16.5px]">Relay</div>
          <div className="text-[11px] text-textFaint">AI email assistant</div>
        </div>
      </div>

      <div className="flex flex-col gap-0.5">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13.5px] font-medium transition-colors ${
                isActive ? "bg-accent/15 text-[#c7c9ff]" : "text-textDim hover:bg-surface2 hover:text-text"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>

      <div className="mt-auto flex flex-col gap-2">
        <button
          className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] font-medium text-textDim hover:bg-surface2 hover:text-text"
          onClick={toggleTheme}
          type="button"
        >
          {theme === "dark" ? "☀️ Light mode" : "🌙 Dark mode"}
        </button>
        <div
          className="border-t border-borderSoft pt-3.5 flex items-center gap-2.5 pl-2 cursor-pointer"
          onClick={logout}
          title="Sign out"
        >
          <div className="w-8 h-8 rounded-full bg-surface3 border border-border flex items-center justify-center text-[12px] font-semibold text-textDim">
            {(email || "?").slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="text-[13px] font-semibold truncate max-w-[140px]">{email}</div>
            <div className="text-[11px] text-textFaint">Sign out</div>
          </div>
        </div>
      </div>
    </div>
  );
}