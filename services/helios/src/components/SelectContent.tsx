import * as React from 'react';
import Avatar from '@mui/material/Avatar';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import MenuItem from '@mui/material/MenuItem';
import ListItemText from '@mui/material/ListItemText';
import ListSubheader from '@mui/material/ListSubheader';
import Select, { selectClasses } from '@mui/material/Select';
import Divider from '@mui/material/Divider';
import DevicesRoundedIcon from '@mui/icons-material/DevicesRounded';

export default function SelectContent() {
  const [company, setCompany] = React.useState('');
  const handleChange = (event: { target: { value: string } }) => {
    setCompany(event.target.value as string);
  };

  return (
    <Select
      labelId="company-select"
      id="company-simple-select"
      value={company}
      onChange={handleChange}
      displayEmpty
      inputProps={{ 'aria-label': 'Select company' }}
      fullWidth
      sx={{
        maxHeight: 56,
        width: 215,
        '&.MuiList-root': { p: '8px' },
        [`& .${selectClasses.select}`]: {
          display: 'flex',
          alignItems: 'center',
          gap: '2px',
          pl: 1,
        },
      }}
    >
      <ListSubheader sx={{ pt: 0 }}>Production</ListSubheader>
      <MenuItem value="">
        <ListItemAvatar sx={{ minWidth: 0, mr: 1.5 }}>
          <Avatar
            alt="Helios workspace"
            sx={{ width: 28, height: 28, bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}
          >
            <DevicesRoundedIcon fontSize="small" />
          </Avatar>
        </ListItemAvatar>
        <ListItemText primary="Complete Automate" secondary="Lead desk" />
      </MenuItem>
      <Divider sx={{ mx: -1 }} />
    </Select>
  );
}
