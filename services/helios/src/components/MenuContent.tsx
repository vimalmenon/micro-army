import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import MailOutlineRoundedIcon from '@mui/icons-material/MailOutlineRounded';
import TrackChangesRoundedIcon from '@mui/icons-material/TrackChangesRounded';
import { useLocation, useNavigate } from 'react-router-dom';
import { useHeliosData } from '../context/HeliosDataContext';

const mainListItems = [
  { text: 'Overview', icon: <HomeRoundedIcon />, to: '/' },
  { text: 'Inbox', icon: <MailOutlineRoundedIcon />, to: '/messages' },
  { text: 'Pipeline', icon: <TrackChangesRoundedIcon />, to: '/leads' },
];

export default function MenuContent() {
  const location = useLocation();
  const navigate = useNavigate();
  const { unreadCount, hotCount } = useHeliosData();

  return (
    <Stack sx={{ flexGrow: 1, p: 1, justifyContent: 'space-between' }} gap={1}>
      <List dense>
        {mainListItems.map((item, index) => {
          const isActive =
            item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to);
          return (
            <ListItem key={index} disablePadding sx={{ display: 'block' }}>
              <ListItemButton
                selected={isActive}
                onClick={() => navigate(item.to)}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
                {item.to === '/messages' && unreadCount > 0 && (
                  <ListItemIcon sx={{ minWidth: 'auto', ml: 'auto' }}>
                    <Stack
                      sx={{
                        bgcolor: 'error.main',
                        color: 'error.contrastText',
                        borderRadius: '12px',
                        px: 1,
                        py: 0.25,
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        lineHeight: 1.2,
                      }}
                    >
                      {unreadCount}
                    </Stack>
                  </ListItemIcon>
                )}
                {item.to === '/leads' && hotCount > 0 && (
                  <ListItemIcon sx={{ minWidth: 'auto', ml: 'auto' }}>
                    <Stack
                      sx={{
                        bgcolor: 'warning.main',
                        color: 'warning.contrastText',
                        borderRadius: '12px',
                        px: 1,
                        py: 0.25,
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        lineHeight: 1.2,
                      }}
                    >
                      {hotCount}
                    </Stack>
                  </ListItemIcon>
                )}
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </Stack>
  );
}
