import { styled } from '@mui/material/styles';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Drawer, { drawerClasses } from '@mui/material/Drawer';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import MenuOpenRoundedIcon from '@mui/icons-material/MenuOpenRounded';
import { useState } from 'react';
import MenuContent from './MenuContent';

const drawerWidth = 240;

const StyledDrawer = styled(Drawer)({
  [`& .${drawerClasses.paper}`]: {
    width: drawerWidth,
    boxSizing: 'border-box',
  },
});

export default function AppNavbar() {
  const [open, setOpen] = useState(false);

  const toggleDrawer = () => setOpen((prev) => !prev);

  return (
    <>
      <Stack
        direction="row"
        sx={{
          display: { xs: 'flex', md: 'none' },
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 1100,
          px: 2,
          py: 1,
          backgroundColor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Stack direction="row" alignItems="center" gap={1}>
          <IconButton aria-label="Open navigation menu" onClick={toggleDrawer}>
            {open ? <MenuOpenRoundedIcon /> : <MenuRoundedIcon />}
          </IconButton>
          <Typography variant="h6" fontWeight={700}>
            Helios
          </Typography>
        </Stack>
      </Stack>
      <StyledDrawer
        anchor="left"
        open={open}
        onClose={toggleDrawer}
        sx={{ display: { xs: 'block', md: 'none' } }}
      >
        <Typography variant="h6" fontWeight={700} sx={{ px: 2, pt: 2, pb: 1 }}>
          ☀️ Helios
        </Typography>
        <Divider />
        <MenuContent />
      </StyledDrawer>
    </>
  );
}
