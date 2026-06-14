import Avatar from '@mui/material/Avatar';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import DevicesRoundedIcon from '@mui/icons-material/DevicesRounded';

export default function SelectContent() {
  return (
    <Stack direction="row" spacing={1.5} alignItems="center" sx={{ maxHeight: 56, width: 215, px: 1 }}>
      <Avatar
        alt="Helios workspace"
        sx={{ width: 28, height: 28, bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}
      >
        <DevicesRoundedIcon fontSize="small" />
      </Avatar>
      <Stack spacing={0}>
        <Typography variant="body2" fontWeight={500}>
          Complete Automate
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Lead desk
        </Typography>
      </Stack>
    </Stack>
  );
}
