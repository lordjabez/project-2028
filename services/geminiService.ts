
import { GoogleGenAI, Type } from "@google/genai";
import type { Candidate } from '../types';

const API_KEY = process.env.API_KEY;
if (!API_KEY) {
  throw new Error("API_KEY environment variable not set");
}

const ai = new GoogleGenAI({ apiKey: API_KEY });

export async function fetchCandidateNames(): Promise<string[]> {
  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: "Identify and list the top 10 potential Democratic presidential candidates for the 2028 US election. For each candidate, provide only their full name.",
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            candidates: {
              type: Type.ARRAY,
              items: {
                type: Type.STRING
              }
            }
          }
        },
      },
    });
    const jsonResponse = JSON.parse(response.text);
    return jsonResponse.candidates || [];
  } catch (error) {
    console.error("Error fetching candidate names:", error);
    throw new Error("Failed to fetch candidate names from Gemini API.");
  }
}

export async function fetchCandidateDetails(name: string): Promise<Candidate> {
  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: `For the potential 2028 presidential candidate ${name}, provide the following information: a one-paragraph biography, a description of a suitable publicly available portrait photo (e.g., 'A professional headshot of the candidate smiling, wearing a suit'), a list of 3 recent, neutral headlines related to their political career, and a list of 3 notable quotes attributed to them.`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            name: { type: Type.STRING },
            photoDescription: { type: Type.STRING },
            bio: { type: Type.STRING },
            headlines: {
              type: Type.ARRAY,
              items: { type: Type.STRING }
            },
            quotes: {
              type: Type.ARRAY,
              items: { type: Type.STRING }
            }
          }
        },
      },
    });
    
    const jsonResponse = JSON.parse(response.text);
    return jsonResponse as Candidate;
  } catch (error) {
    console.error(`Error fetching details for ${name}:`, error);
    // Return a partial object on failure to avoid breaking the entire list
    return {
      name,
      photoDescription: "Information currently unavailable.",
      bio: "Failed to load biography.",
      headlines: ["Could not retrieve headlines."],
      quotes: ["Could not retrieve quotes."],
    };
  }
}
