import { useEffect } from 'react';
import { Navigate, useLocation, useMatch } from 'react-router-dom';

import { useHeliosData } from './context/HeliosDataContext';
import { DashboardPage } from './pages/DashboardPage';
import { LeadDetailPage } from './pages/LeadDetailPage';
import { LeadsPage } from './pages/LeadsPage';
import { MessageDetailPage } from './pages/MessageDetailPage';
import { MessagesPage } from './pages/MessagesPage';
import { ServicesPage } from './pages/ServicesPage';

// MUI imports
import { alpha } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import AppNavbar from './components/AppNavbar';
import Header from './components/Header';
import SideMenu from './components/SideMenu';
import AppTheme from './AppTheme';

function getPrimaryContent(pathname: string): React.ReactNode {
  if (pathname === '/') return <DashboardPage />;
  if (pathname === '/messages') return <MessagesPage />;
  if (pathname === '/leads') return <LeadsPage />;
  if (pathname === '/services') return <ServicesPage />;
  return <Navigate to="/" replace />;
}

export default function App() {
  const { fetchLeadDetail } = useHeliosData();
  const location = useLocation();
  const messageDetailMatch = useMatch('/messages/:messageId');
  const leadDetailMatch = useMatch('/leads/:leadId');

  const isMessagesRoute = location.pathname === '/messages' || Boolean(messageDetailMatch);
  const isLeadsRoute = location.pathname === '/leads' || Boolean(leadDetailMatch);
  const isServicesRoute = location.pathname === '/services';
  const isKnownRoute = location.pathname === '/' || isMessagesRoute || isLeadsRoute || isServicesRoute;

  useEffect(() => {
    const leadId = leadDetailMatch?.params.leadId;
    if (leadId) {
      fetchLeadDetail(leadId);
    }
  }, [fetchLeadDetail, leadDetailMatch]);

  const content = (() => {
    if (messageDetailMatch) return <MessageDetailPage />;
    if (leadDetailMatch) return <LeadDetailPage />;
    return getPrimaryContent(location.pathname);
  })();

  if (!isKnownRoute) {
    return <Navigate to="/" replace />;
  }

  return (
    <AppTheme>
      <CssBaseline enableColorScheme />
      <Box sx={{ display: 'flex' }}>
        <SideMenu />
        <AppNavbar />
        <Box
          component="main"
          sx={(theme) => ({
            flexGrow: 1,
            backgroundColor: theme.vars
              ? `rgba(${theme.vars.palette.background.defaultChannel} / 1)`
              : alpha(theme.palette.background.default, 1),
            overflow: 'auto',
          })}
        >
          <Stack
            spacing={2}
            sx={{
              alignItems: 'center',
              mx: 3,
              pb: 5,
              mt: { xs: 8, md: 0 },
            }}
          >
            <Header />
            <Box sx={{ width: '100%', maxWidth: { sm: '100%', md: '1700px' } }}>
              {content}
            </Box>
          </Stack>
        </Box>
      </Box>
    </AppTheme>
  );
}
