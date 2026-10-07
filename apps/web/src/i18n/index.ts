import { fr } from './fr';
import { en } from './en';

export type Language = 'fr' | 'en';
export type TranslationDict = typeof fr;

export const translations: Record<Language, TranslationDict> = {
  fr,
  en,
};
