"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ArrowLeftRight,
  Bell,
  Bot,
  ClipboardCheck,
  FileText,
  FolderKanban,
  LayoutDashboard,
  LibraryBig,
  ListTodo,
  MessagesSquare,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { WorkspaceSwitcher } from "@/components/layout/workspace-switcher";
import { NavUser } from "@/components/layout/nav-user";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import { ROUTES } from "@/lib/constants";
import { REVIEWER_ROLES } from "@/types/workspace";

const NAV_MAIN = [
  { title: "Dashboard", href: ROUTES.dashboard, icon: LayoutDashboard },
  { title: "Projects", href: ROUTES.projects, icon: FolderKanban },
  { title: "Tasks", href: ROUTES.tasks, icon: ListTodo },
  { title: "Handovers", href: ROUTES.handovers, icon: ArrowLeftRight },
  { title: "Documents", href: ROUTES.documents, icon: FileText },
  { title: "Activity", href: ROUTES.activity, icon: Activity },
  { title: "Notifications", href: ROUTES.notifications, icon: Bell },
  { title: "Search", href: ROUTES.search, icon: Search },
];

// Shown only to roles that can review handovers.
const NAV_REVIEWS = {
  title: "Reviews",
  href: ROUTES.handoverReviews,
  icon: ClipboardCheck,
};

const NAV_AI = [
  { title: "AI Assistant", href: ROUTES.ai, icon: Sparkles, exact: true },
  { title: "AI Chat", href: ROUTES.aiChat, icon: MessagesSquare },
  { title: "AI Search", href: ROUTES.aiSearch, icon: Bot },
  { title: "Prompt Library", href: ROUTES.aiTemplates, icon: LibraryBig },
];

const NAV_FOOTER = [{ title: "Settings", href: ROUTES.settings, icon: Settings }];

export function AppSidebar() {
  const pathname = usePathname();
  const { activeWorkspace } = useWorkspaceContext();

  const canReview =
    !!activeWorkspace?.role && REVIEWER_ROLES.includes(activeWorkspace.role);
  const navMain = canReview ? [...NAV_MAIN, NAV_REVIEWS] : NAV_MAIN;

  const isActive = (href: string) => {
    if (href === ROUTES.dashboard) return pathname === href;
    // Keep "Handovers" from lighting up while on the "Reviews" sub-page.
    if (href === ROUTES.handovers && pathname.startsWith(ROUTES.handoverReviews))
      return false;
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <WorkspaceSwitcher />
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Platform</SidebarGroupLabel>
          <SidebarMenu>
            {navMain.map((item) => (
              <SidebarMenuItem key={item.href}>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(item.href)}
                  tooltip={item.title}
                >
                  <Link href={item.href}>
                    <item.icon />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>AI</SidebarGroupLabel>
          <SidebarMenu>
            {NAV_AI.map((item) => (
              <SidebarMenuItem key={item.href}>
                <SidebarMenuButton
                  asChild
                  isActive={
                    "exact" in item && item.exact
                      ? pathname === item.href
                      : isActive(item.href)
                  }
                  tooltip={item.title}
                >
                  <Link href={item.href}>
                    <item.icon />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>

        <SidebarGroup className="mt-auto">
          <SidebarMenu>
            {NAV_FOOTER.map((item) => (
              <SidebarMenuItem key={item.href}>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(item.href)}
                  tooltip={item.title}
                >
                  <Link href={item.href}>
                    <item.icon />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
