import { useNavigate, useParams } from 'react-router-dom';
import { useHeliosData } from '../context/HeliosDataContext';
import { formatDate, formatTime } from '../lib/helios';
import type { Message } from '../lib/types';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';
import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';

export function MessageDetailPage() {
  const navigate = useNavigate();
  const { messageId } = useParams();
  const { messages, markRead, deleteMessage } = useHeliosData();
  const message = messages.find((m: Message) => m.id === messageId) ?? null;

  if (!message) {
    return (
      <Box sx={{ py: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">Message not found.</Typography>
        <Button onClick={() => navigate('/messages')} sx={{ mt: 2 }}>
          Back to Inbox
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 800 }}>
      <Button
        startIcon={<ArrowBackRoundedIcon />}
        onClick={() => navigate('/messages')}
        sx={{ mb: 2, color: 'text.secondary' }}
      >
        Messages
      </Button>

      <Card variant="outlined">
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
            <Box>
              <Typography variant="h5" fontWeight={700}>
                {message.subject}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {message.name} &lt;{message.email}&gt;
              </Typography>
            </Box>
            <Stack direction="row" gap={1} alignItems="center">
              <Chip
                label={message.read ? 'Read' : 'Unread'}
                color={message.read ? 'default' : 'primary'}
                size="small"
              />
              <Typography variant="caption" color="text.secondary">
                <Box>{formatTime(message.created_at)}</Box>
                <Box>{formatDate(message.created_at)}</Box>
              </Typography>
            </Stack>
          </Stack>

          <Box
            sx={{
              mt: 3,
              p: 2,
              bgcolor: 'grey.50',
              borderRadius: 1,
              whiteSpace: 'pre-wrap',
              typography: 'body2',
              lineHeight: 1.8,
            }}
          >
            {message.message}
          </Box>

          <Stack direction="row" gap={1} sx={{ mt: 3 }}>
            {!message.read && (
              <Button
                variant="contained"
                size="small"
                startIcon={<CheckCircleOutlineRoundedIcon />}
                onClick={() => {
                  markRead(message.id);
                  navigate('/messages');
                }}
              >
                Mark Read
              </Button>
            )}
            <Button
              variant="outlined"
              color="error"
              size="small"
              startIcon={<DeleteOutlineRoundedIcon />}
              onClick={() => {
                if (globalThis.confirm('Delete this message?')) {
                  deleteMessage(message.id);
                  navigate('/messages');
                }
              }}
            >
              Delete
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
