import type { PublicChatSession } from '../../public/ai-chat/chat.types';

export const PAGE_SIZE = 20;

export type AiEscalationListItem = {
	id: number;
	public_chat_id: string;
	user_intention: string;
	created_at: string;
	message_count: number;
};

export type AiEscalationList = {
	items: AiEscalationListItem[];
	total: number;
	limit: number;
	offset: number;
};

export type AiEscalationDetail = {
	id: number;
	public_chat_id: string;
	user_intention: string;
	created_at: string;
	session: PublicChatSession;
};
