import Typography from '@mui/material/Typography';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import { useLocation } from 'react-router-dom';

const pathLabels: Record<string, string> = {
  '': 'Dashboard',
  'messages': 'Inbox',
  'leads': 'Pipeline',
  'services': 'Services',
};

export default function NavbarBreadcrumbs() {
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);
  // Show current page as last segment, no links
  const crumbs = segments.length === 0
    ? ['Dashboard']
    : segments.map((s) => pathLabels[s] || s);

  return (
    <Breadcrumbs aria-label="breadcrumb">
      {crumbs.map((crumb, i) =>
        i < crumbs.length - 1 ? (
          <Link key={crumb} color="inherit" href="#">
            {crumb}
          </Link>
        ) : (
          <Typography key={crumb} sx={{ color: 'text.primary', fontWeight: 600 }}>
            {crumb}
          </Typography>
        ),
      )}
    </Breadcrumbs>
  );
}
