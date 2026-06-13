import * as React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import type { ThemeOptions } from '@mui/material/styles';
import { chartsCustomizations } from './theme/customizations/charts';
import { dataGridCustomizations } from './theme/customizations/dataGrid';
import { datePickersCustomizations } from './theme/customizations/datePickers';
import { treeViewCustomizations } from './theme/customizations/treeView';

const xThemeComponents = {
  ...chartsCustomizations,
  ...dataGridCustomizations,
  ...datePickersCustomizations,
  ...treeViewCustomizations,
};

const defaultTheme: ThemeOptions = {
  colorSchemes: {
    light: {
      palette: {
        primary: {
          light: '#4dd0e1',
          main: '#00bcd4',
          dark: '#008394',
          contrastText: '#fff',
        },
        secondary: {
          light: '#ff80ab',
          main: '#f50057',
          dark: '#c51162',
          contrastText: '#fff',
        },
        background: {
          default: '#f5f5f5',
          paper: '#ffffff',
        },
      },
    },
    dark: {
      palette: {
        primary: {
          light: '#4dd0e1',
          main: '#26c6da',
          dark: '#00acc1',
          contrastText: '#fff',
        },
        background: {
          default: '#0f172a',
          paper: '#1e293b',
        },
        divider: 'rgba(226, 232, 240, 0.12)',
        text: {
          primary: '#e2e8f0',
          secondary: '#94a3b8',
        },
      },
    },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: { boxShadow: 'none' },
      },
    },
    MuiCardContent: {
      styleOverrides: {
        root: {
          '&:last-child': { paddingBottom: 16 },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: '1px solid',
          borderColor: 'divider',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          margin: '2px 0',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500 },
      },
    },
    ...xThemeComponents,
  },
};

export default function AppTheme({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const theme = React.useMemo(() => createTheme(defaultTheme), []);
  return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
}
