// Demo data for testing the split-view UI without backend
// This simulates the v2 API response format

export interface DemoCitation {
  source_id: string;
  paragraph_id: string;
  relevance_score: number;
  text_snippet: string;
}

export interface DemoTranslation {
  simplified: string;
  metaphor: string;
  grade_level: string;
}

export interface DemoQueryResponse {
  answer: string;
  sources: DemoCitation[];
  translation: DemoTranslation;
  confidence: number;
  follow_up_questions: string[];
}

// Demo responses for common questions about photosynthesis
export const demoResponses: Record<string, DemoQueryResponse> = {
  "what is photosynthesis": {
    answer: "Photosynthesis is the biological process by which plants, algae, and some bacteria convert light energy from the sun into chemical energy stored in glucose molecules. This process is essential for life on Earth as it produces oxygen as a byproduct and forms the foundation of most food chains.",
    sources: [
      {
        source_id: "photosynthesis-101",
        paragraph_id: "para-1",
        relevance_score: 0.95,
        text_snippet: "Photosynthesis is the process by which plants convert light energy from the sun into chemical energy stored in glucose. This fundamental biological process is essential for life on Earth, as it produces oxygen and forms the base of most food chains."
      },
      {
        source_id: "photosynthesis-101",
        paragraph_id: "para-3",
        relevance_score: 0.88,
        text_snippet: "Photosynthesis can be summarized by the chemical equation: 6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂. This means that carbon dioxide and water, in the presence of light, produce glucose and oxygen."
      }
    ],
    translation: {
      simplified: "Photosynthesis is how plants make their food using sunlight. They take in carbon dioxide from the air and water from the soil, then use sunlight to turn these into glucose (sugar) for energy. They also release oxygen, which humans and animals need to breathe.",
      metaphor: "Think of photosynthesis like a solar-powered kitchen inside plant leaves. The kitchen takes sunlight (solar power), water, and air as ingredients, then cooks up glucose (food) while releasing oxygen as a sort of exhaust that we breathe!",
      grade_level: "6th grade"
    },
    confidence: 0.92,
    follow_up_questions: [
      "Where does photosynthesis happen in plants?",
      "What are the two stages of photosynthesis?",
      "What factors affect the rate of photosynthesis?"
    ]
  },

  "light energy": {
    answer: "Light energy conversion occurs in two main stages. First, during the light-dependent reactions, chlorophyll in the chloroplasts captures light energy from the sun. This energy is used to split water molecules and produce ATP and NADPH, which are energy-carrying molecules. Then, in the Calvin cycle, this stored energy is used to convert carbon dioxide into glucose.",
    sources: [
      {
        source_id: "photosynthesis-101",
        paragraph_id: "para-4",
        relevance_score: 0.93,
        text_snippet: "The process consists of two main stages: the light-dependent reactions and the Calvin cycle (light-independent reactions). During the light-dependent reactions, energy from sunlight is captured and used to produce ATP and NADPH, energy-carrying molecules."
      },
      {
        source_id: "photosynthesis-101",
        paragraph_id: "para-5",
        relevance_score: 0.89,
        text_snippet: "The Calvin cycle uses the ATP and NADPH from the light-dependent reactions to convert carbon dioxide into glucose. This cycle is named after Melvin Calvin, who discovered it in 1950 and was awarded the Nobel Prize for this work."
      }
    ],
    translation: {
      simplified: "Plants have a two-step process for using sunlight. First, they capture the sun's energy and store it in special 'batteries' called ATP and NADPH. Then, they use that stored energy to turn carbon dioxide into sugar (glucose) that the plant can use for food.",
      metaphor: "It's like charging a battery with sunlight! First, the plant captures sunlight like a solar panel charging up batteries (ATP and NADPH). Then it uses those charged batteries to power a factory that turns carbon dioxide into sugar.",
      grade_level: "7th grade"
    },
    confidence: 0.88,
    follow_up_questions: [
      "What is the Calvin cycle?",
      "How do plants capture different colors of light?",
      "What is chlorophyll?"
    ]
  },

  "factors affect": {
    answer: "Several key factors influence the rate of photosynthesis: light intensity, carbon dioxide concentration, temperature, and water availability. Light provides the energy needed for the process, carbon dioxide is the raw material, temperature affects enzyme activity, and water is essential for the light-dependent reactions.",
    sources: [
      {
        source_id: "photosynthesis-101",
        paragraph_id: "para-6",
        relevance_score: 0.97,
        text_snippet: "Several factors affect the rate of photosynthesis, including light intensity, carbon dioxide concentration, temperature, and water availability. Plants have evolved various adaptations to optimize photosynthesis under different environmental conditions."
      }
    ],
    translation: {
      simplified: "Photosynthesis needs four things to work well: enough light, enough carbon dioxide, the right temperature (not too hot or cold), and enough water. If any of these are missing or too low, photosynthesis slows down.",
      metaphor: "Photosynthesis is like a recipe that needs all the right ingredients in the right amounts. Just as a cake needs the right temperature in the oven and all the ingredients, photosynthesis needs light, carbon dioxide, warmth, and water to make the plant's food.",
      grade_level: "5th grade"
    },
    confidence: 0.95,
    follow_up_questions: [
      "How do plants adapt to low light conditions?",
      "What happens if temperature is too high?",
      "Do all plants need the same amount of water?"
    ]
  },

  "default": {
    answer: "That's a great question about photosynthesis! Based on the textbook content, I can help explain this topic. Photosynthesis is a complex process with many fascinating aspects, from how plants capture light energy to how they produce the oxygen we breathe.",
    sources: [
      {
        source_id: "photosynthesis-101",
        paragraph_id: "para-1",
        relevance_score: 0.75,
        text_snippet: "Photosynthesis is the process by which plants convert light energy from the sun into chemical energy stored in glucose. This fundamental biological process is essential for life on Earth, as it produces oxygen and forms the base of most food chains."
      },
      {
        source_id: "photosynthesis-101",
        paragraph_id: "para-10",
        relevance_score: 0.68,
        text_snippet: "Understanding photosynthesis is fundamental to many fields, including agriculture, bioenergy, and climate science. Scientists continue to study this process to develop more efficient crops and sustainable energy solutions."
      }
    ],
    translation: {
      simplified: "Photosynthesis is how plants make food using sunlight. This is really important because it gives us oxygen to breathe and is the base of the food chain.",
      metaphor: "Plants are like nature's solar panels - they turn sunlight into energy while providing fresh air for us to breathe!",
      grade_level: "4th grade"
    },
    confidence: 0.72,
    follow_up_questions: [
      "What is photosynthesis?",
      "How does light energy get converted?",
      "What factors affect photosynthesis?"
    ]
  }
};

export function getDemoResponse(query: string): DemoQueryResponse | null {
  const lowerQuery = query.toLowerCase();

  for (const [key, response] of Object.entries(demoResponses)) {
    if (lowerQuery.includes(key)) {
      return response;
    }
  }

  return demoResponses["default"];
}
