import { command } from '$app/server';
import { ApiError, apiFetch } from '$lib/server/api';
import {
	PublicChatUnavailableError,
	type PublicChatSendRequest,
	type PublicChatSendResponse
} from './chat.types';

export const sendPublicMessage = command<PublicChatSendRequest, PublicChatSendResponse>(
	'unchecked',
	async ({ chat_id, content }) => {
		try {
			return await apiFetch<PublicChatSendResponse>(
				'/public/ai-chat',
				{ method: 'POST', body: { chat_id, content } },
				null
			);
		} catch (err) {
			if (err instanceof ApiError) {
				const body = err.body as
					| { message?: string; chat_id?: string }
					| string
					| null;
				const messageFromBody =
					body && typeof body === 'object' && typeof body.message === 'string'
						? body.message
						: undefined;
				const chatIdFromBody =
					body && typeof body === 'object' && typeof body.chat_id === 'string'
						? body.chat_id
						: null;
				throw new PublicChatUnavailableError(
					err.status,
					messageFromBody,
					chatIdFromBody
				);
			}
			throw err;
		}
	}
);
