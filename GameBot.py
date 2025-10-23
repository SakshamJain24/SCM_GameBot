import streamlit as st
import json
from datetime import datetime
import google.generativeai as genai
import plotly.graph_objects as go
import pandas as pd

# Configure Gemini API
genai.configure(api_key="AIzaSyCo1TgO60NwadRjwit5Qhc4CmschHsRsCE")

# Page config
st.set_page_config(page_title="SCM Game Bot", page_icon="🏭", layout="wide")

# Custom CSS for better visuals
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-top: 0;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    .metric-box {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'game_state' not in st.session_state:
    st.session_state.game_state = {
        'stage': 0,
        'scenario': 0,
        'client_type': 'TechCo',
        'scores': {
            'cost_efficiency': 100,
            'customer_satisfaction': 100,
            'resilience': 100,
            'sustainability': 100
        },
        'decisions': [],
        'feedback_history': [],
        'current_scenario': None,
        'decision_made': False,
        'selected_choice': None
    }

# SCM Game Prompt Template
SCM_GAME_PROMPT = """You are an AI Game Master for a Supply Chain Management training simulation. 

GAME CONTEXT:
- Player role: Supply Chain Consultant
- Client: {client_type}
- Current Stage: {stage_name}
- Scenario: {scenario_number}
- Current Scores: Cost Efficiency: {cost}%, Customer Satisfaction: {satisfaction}%, Resilience: {resilience}%, Sustainability: {sustainability}%

GAME STAGES:
1. Planning (Demand forecasting, inventory strategy)
2. Sourcing (Supplier selection, procurement)
3. Manufacturing (Production planning, quality control)
4. Delivery/Logistics (Transportation, distribution)
5. Returns/After-sales (Defect management, recycling)

YOUR TASK:
Generate a realistic supply chain scenario for {client_type} at the {stage_name} stage.

IMPORTANT: The impacts should be significant. Use values between -15 and +15 for each metric.
Make trade-offs meaningful - good decisions should have both positive and negative impacts.

FORMAT YOUR RESPONSE AS VALID JSON ONLY (no markdown, no code blocks):
{{
    "scenario_title": "Brief title",
    "scenario_description": "Detailed description of the challenge (2-3 sentences)",
    "context": "Additional business context if needed",
    "options": [
        {{
            "id": "A",
            "text": "Option description",
            "impact": {{
                "cost_efficiency": -15 to +15,
                "customer_satisfaction": -15 to +15,
                "resilience": -15 to +15,
                "sustainability": -15 to +15
            }},
            "feedback": "What happens if this option is chosen"
        }},
        {{
            "id": "B",
            "text": "Option description",
            "impact": {{
                "cost_efficiency": -15 to +15,
                "customer_satisfaction": -15 to +15,
                "resilience": -15 to +15,
                "sustainability": -15 to +15
            }},
            "feedback": "What happens if this option is chosen"
        }},
        {{
            "id": "C",
            "text": "Option description",
            "impact": {{
                "cost_efficiency": -15 to +15,
                "customer_satisfaction": -15 to +15,
                "resilience": -15 to +15,
                "sustainability": -15 to +15
            }},
            "feedback": "What happens if this option is chosen"
        }},
        {{
            "id": "D",
            "text": "Option description",
            "impact": {{
                "cost_efficiency": -15 to +15,
                "customer_satisfaction": -15 to +15,
                "resilience": -15 to +15,
                "sustainability": -15 to +15
            }},
            "feedback": "What happens if this option is chosen"
        }}
    ],
    "learning_point": "Key SCM concept illustrated by this scenario"
}}

Previous decisions: {previous_decisions}
Make the scenario logically connected to previous choices when applicable.
Return ONLY the JSON object, no additional text or markdown formatting.
"""

# Stage definitions
STAGES = [
    "Planning",
    "Sourcing", 
    "Manufacturing",
    "Delivery/Logistics",
    "Returns/After-sales"
]

# Client options
CLIENT_TYPES = {
    "TechCo": "A smartphone manufacturer facing global supply chain challenges",
    "FMCG Corp": "A fast-moving consumer goods company with extensive distribution needs",
    "PharmaCare": "A pharmaceutical manufacturer with strict quality requirements",
    "AutoDrive": "An automotive manufacturer dealing with complex supplier networks"
}


def extract_json_from_text(text):
    """Extract JSON from text that might contain markdown code blocks or extra text"""
    # Try to find JSON in code blocks
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()
    
    # Try to find JSON object boundaries
    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1
    
    if start_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx]
    
    return text


def get_scenario_from_gemini(client_type, stage_name, scenario_number, scores, previous_decisions):
    """Fetch scenario from Gemini API with robust error handling"""
    
    # Format the prompt
    prompt = SCM_GAME_PROMPT.format(
        client_type=client_type,
        stage_name=stage_name,
        scenario_number=scenario_number,
        cost=scores['cost_efficiency'],
        satisfaction=scores['customer_satisfaction'],
        resilience=scores['resilience'],
        sustainability=scores['sustainability'],
        previous_decisions=json.dumps(previous_decisions[-3:]) if previous_decisions else "None"
    )
    
    try:
        # Create model instance
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        
        # Call the model with JSON mode
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.7
            }
        )
        
        # Get response text
        response_text = response.text
        
        # Try to parse JSON
        try:
            scenario = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown or extra text
            cleaned_text = extract_json_from_text(response_text)
            scenario = json.loads(cleaned_text)
        
        # Validate scenario structure
        required_fields = ['scenario_title', 'scenario_description', 'options', 'learning_point']
        if not all(field in scenario for field in required_fields):
            raise ValueError("Missing required fields in scenario")
        
        # Validate options
        if len(scenario['options']) < 3:
            raise ValueError("Not enough options in scenario")
        
        for option in scenario['options']:
            if not all(key in option for key in ['id', 'text', 'impact', 'feedback']):
                raise ValueError("Invalid option structure")
        
        return scenario
        
    except Exception as e:
        st.error(f"⚠️ Error generating scenario: {str(e)}")
        # Return a fallback scenario
        return create_fallback_scenario(stage_name)


def create_fallback_scenario(stage_name):
    """Create a fallback scenario if LLM fails"""
    return {
        "scenario_title": f"{stage_name} Challenge",
        "scenario_description": "Your team needs to make a critical decision to optimize the supply chain.",
        "context": "This is a standard scenario while we resolve technical issues.",
        "options": [
            {
                "id": "A",
                "text": "Take the conservative approach focusing on cost savings",
                "impact": {"cost_efficiency": 10, "customer_satisfaction": -5, "resilience": 0, "sustainability": -5},
                "feedback": "You saved costs but may have compromised other areas."
            },
            {
                "id": "B", 
                "text": "Balance all factors with a moderate investment",
                "impact": {"cost_efficiency": 0, "customer_satisfaction": 5, "resilience": 5, "sustainability": 5},
                "feedback": "A balanced approach that maintains stability."
            },
            {
                "id": "C",
                "text": "Invest heavily in innovation and sustainability",
                "impact": {"cost_efficiency": -10, "customer_satisfaction": 10, "resilience": 10, "sustainability": 15},
                "feedback": "Higher costs but strong long-term benefits."
            }
        ],
        "learning_point": f"Understanding trade-offs in {stage_name} decisions"
    }


def generate_performance_analysis(scores, decisions, feedback_history, client_type):
    """Generate detailed performance analysis using Gemini"""
    
    # Calculate metrics
    score_changes = {metric: value - 100 for metric, value in scores.items()}
    avg_score = sum(scores.values()) / len(scores)
    
    # Build decision summary
    decision_summary = []
    for decision in decisions:
        decision_summary.append(f"Stage: {decision['stage']}, Choice: {decision['choice']}")
    
    prompt = f"""You are an expert Supply Chain Management consultant providing personalized feedback to a trainee.

CLIENT: {client_type}
FINAL SCORES:
- Cost Efficiency: {scores['cost_efficiency']}% (Change: {score_changes['cost_efficiency']:+d}%)
- Customer Satisfaction: {scores['customer_satisfaction']}% (Change: {score_changes['customer_satisfaction']:+d}%)
- Resilience: {scores['resilience']}% (Change: {score_changes['resilience']:+d}%)
- Sustainability: {scores['sustainability']}% (Change: {score_changes['sustainability']:+d}%)
- Average Score: {avg_score:.1f}%

DECISIONS MADE:
{chr(10).join(decision_summary)}

Provide a detailed, personalized analysis in JSON format:
{{
    "overview": "2-3 sentence summary of their overall performance and decision-making pattern",
    "strengths": ["3-4 specific strengths based on their scores and decisions"],
    "improvements": ["3-4 specific areas where they can improve, with actionable advice"],
    "personal_learnings": ["4-5 key learnings they should take away from this game based on their actual decisions"],
    "recommendations": "A paragraph of specific recommendations for how they can apply these learnings in real-world SCM scenarios"
}}

Make the analysis highly personalized based on their actual scores and decision patterns. Be constructive and specific.
Return ONLY the JSON object."""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.7
            }
        )
        
        response_text = response.text
        
        try:
            analysis = json.loads(response_text)
        except json.JSONDecodeError:
            cleaned_text = extract_json_from_text(response_text)
            analysis = json.loads(cleaned_text)
        
        return analysis
        
    except Exception as e:
        st.error(f"Could not generate detailed analysis: {str(e)}")
        return {
            "overview": "You completed the simulation successfully!",
            "strengths": ["Completed all stages", "Made strategic decisions"],
            "improvements": ["Consider balancing all metrics", "Think about long-term impacts"],
            "personal_learnings": ["Supply chains require trade-offs", "Different decisions affect different metrics"],
            "recommendations": "Continue learning about supply chain management principles."
        }


def calculate_score_change(current_scores, impact):
    """Calculate new scores based on impact"""
    new_scores = {}
    for metric, value in current_scores.items():
        if metric in impact:
            new_value = value + impact[metric]
            new_scores[metric] = max(0, min(100, new_value))
        else:
            new_scores[metric] = value
    return new_scores


def render_dashboard(scores):
    """Create performance dashboard"""
    fig = go.Figure()
    
    categories = ['Cost Efficiency', 'Customer Satisfaction', 'Resilience', 'Sustainability']
    values = [scores['cost_efficiency'], scores['customer_satisfaction'], 
              scores['resilience'], scores['sustainability']]
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Performance',
        line_color='rgb(102, 126, 234)',
        fillcolor='rgba(102, 126, 234, 0.5)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10)
            )
        ),
        showlegend=False,
        height=400,
        margin=dict(l=80, r=80, t=40, b=40)
    )
    
    return fig


def render_progress_bar():
    """Render game progress"""
    stage = st.session_state.game_state['stage']
    scenario = st.session_state.game_state['scenario']
    
    if stage > 0 and stage <= len(STAGES):
        total_scenarios = len(STAGES) * 2  # 2 scenarios per stage
        current_progress = ((stage - 1) * 2 + scenario)
        progress = current_progress / total_scenarios
        
        st.markdown("### 📊 Game Progress")
        st.progress(progress)
        st.caption(f"Stage {stage} of {len(STAGES)} • Scenario {scenario + 1} of 2")


def main():
    # Header
    st.markdown('<h1 class="main-header">🏭 Supply Chain Management Game</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Step into the role of a Supply Chain Consultant and navigate real-world challenges</p>', unsafe_allow_html=True)
    
    # Sidebar for game info
    with st.sidebar:
        st.markdown("## 📊 Game Status")
        
        if st.session_state.game_state['stage'] > 0:
            # Current stage display
            stage_idx = st.session_state.game_state['stage'] - 1
            if stage_idx < len(STAGES):
                st.info(f"**Current Stage:** {STAGES[stage_idx]}")
            
            # Progress bar
            render_progress_bar()
            
            st.markdown("---")
            st.markdown("### Performance Metrics")
            
            # Score cards with colors
            scores = st.session_state.game_state['scores']
            
            for metric, value in scores.items():
                label = metric.replace('_', ' ').title()
                if value >= 80:
                    color = "🟢"
                elif value >= 60:
                    color = "🟡"
                else:
                    color = "🔴"
                
                st.metric(
                    f"{color} {label}", 
                    f"{value}%",
                    delta=f"{value - 100:+d}%"
                )
        
        st.markdown("---")
        
        if st.button("🔄 Restart Game", type="secondary", width='stretch'):
            st.session_state.game_state = {
                'stage': 0,
                'scenario': 0,
                'client_type': 'TechCo',
                'scores': {
                    'cost_efficiency': 100,
                    'customer_satisfaction': 100,
                    'resilience': 100,
                    'sustainability': 100
                },
                'decisions': [],
                'feedback_history': [],
                'current_scenario': None,
                'decision_made': False,
                'selected_choice': None
            }
            st.rerun()
    
    # Main game area
    if st.session_state.game_state['stage'] == 0:
        # Introduction screen
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### Welcome to the SCM Simulation! 🎮")
            
            with st.expander("📚 What is Supply Chain Management?", expanded=True):
                st.markdown("""
                Supply Chain Management ensures products move smoothly from planning to delivery. It covers **5 critical stages**:
                
                1. **📋 Planning** - Demand forecasting & inventory strategy
                2. **🤝 Sourcing** - Supplier selection & procurement
                3. **🏭 Manufacturing** - Production planning & quality control
                4. **🚚 Delivery** - Transportation & distribution logistics
                5. **↩️ Returns** - Defect management & recycling
                """)
            
            with st.expander("🎯 Understanding Key Metrics"):
                st.markdown("""
                Your decisions will be evaluated across four critical dimensions:
                
                **💰 Cost Efficiency**
                - Measures how well you manage operational costs and resource utilization
                - Includes procurement costs, inventory holding costs, and operational expenses
                - Higher scores indicate better financial performance
                
                **😊 Customer Satisfaction**
                - Reflects how well you meet customer expectations
                - Includes delivery speed, product quality, and service reliability
                - Critical for brand reputation and repeat business
                
                **🛡️ Resilience**
                - Measures your supply chain's ability to handle disruptions
                - Includes backup suppliers, contingency planning, and risk management
                - Essential for business continuity during crises
                
                **🌱 Sustainability**
                - Evaluates environmental and social responsibility
                - Includes carbon footprint, ethical sourcing, and waste management
                - Increasingly important for modern businesses and regulations
                
                *Note: These metrics often compete with each other. Great supply chain managers find the right balance!*
                """)
            
            with st.expander("🎯 Game Rules"):
                st.markdown("""
                - Play as a **Supply Chain Consultant**
                - Solve **real-world challenges** for your client
                - Navigate through **5 stages**, each with multiple scenarios
                - Your choices impact **4 key metrics** (sometimes positively, sometimes negatively)
                - Receive instant feedback and learning points
                - Get a detailed performance analysis at the end
                """)
            
            st.markdown("---")
            st.markdown("### 🏢 Select Your Client")
            
            client = st.selectbox(
                "Choose your client company:",
                options=list(CLIENT_TYPES.keys()),
                format_func=lambda x: f"{x} - {CLIENT_TYPES[x]}",
                label_visibility="collapsed"
            )
            st.session_state.game_state['client_type'] = client
            
            st.markdown("")
            
            if st.button("🎮 Start Game", type="primary", width='stretch'):
                st.session_state.game_state['stage'] = 1
                st.session_state.game_state['scenario'] = 0
                st.rerun()
    
    elif st.session_state.game_state['stage'] <= len(STAGES):
        # Game in progress
        stage_idx = st.session_state.game_state['stage'] - 1
        current_stage = STAGES[stage_idx]
        
        st.markdown(f"## 🎯 Stage {st.session_state.game_state['stage']}: {current_stage}")
        
        # Get or use cached scenario
        if not st.session_state.game_state['decision_made'] and st.session_state.game_state['current_scenario'] is None:
            with st.spinner("🤔 Generating scenario..."):
                scenario = get_scenario_from_gemini(
                    st.session_state.game_state['client_type'],
                    current_stage,
                    st.session_state.game_state['scenario'],
                    st.session_state.game_state['scores'],
                    st.session_state.game_state['decisions']
                )
                st.session_state.game_state['current_scenario'] = scenario
        else:
            scenario = st.session_state.game_state['current_scenario']
        
        # Display scenario
        if scenario and not st.session_state.game_state['decision_made']:
            st.markdown(f"### 📌 {scenario.get('scenario_title', 'Scenario')}")
            st.markdown(scenario.get('scenario_description', ''))
            
            if 'context' in scenario and scenario['context']:
                st.info(f"💡 **Context:** {scenario['context']}")
            
            st.markdown("")
            
            # Display options
            st.markdown("### 🎲 Your Options:")
            st.markdown("")
            
            cols = st.columns(2)
            for idx, option in enumerate(scenario.get('options', [])):
                with cols[idx % 2]:
                    if st.button(
                        f"**Option {option['id']}**\n\n{option['text']}", 
                        key=f"opt_{option['id']}",
                        width='stretch',
                        type="secondary"
                    ):
                        st.session_state.game_state['selected_choice'] = option
                        st.session_state.game_state['decision_made'] = True
                        st.rerun()
        
        # Show feedback if decision made
        elif st.session_state.game_state['decision_made'] and st.session_state.game_state['selected_choice']:
            choice = st.session_state.game_state['selected_choice']
            scenario = st.session_state.game_state['current_scenario']
            
            # Store decision first (before updating scores)
            if len(st.session_state.game_state['decisions']) == 0 or \
               st.session_state.game_state['decisions'][-1].get('timestamp') != 'current':
                st.session_state.game_state['decisions'].append({
                    'stage': current_stage,
                    'scenario': scenario.get('scenario_title', ''),
                    'choice': choice['text'],
                    'timestamp': 'current'
                })
            
            # Update scores
            new_scores = calculate_score_change(
                st.session_state.game_state['scores'],
                choice['impact']
            )
            st.session_state.game_state['scores'] = new_scores
            
            # Display feedback
            st.success("✅ Decision Recorded Successfully!")
            
            st.markdown(f"**📊 Impact:** {choice['feedback']}")
            
            # Show score changes
            st.markdown("**Score Changes:**")
            cols = st.columns(4)
            for idx, (metric, change) in enumerate(choice['impact'].items()):
                with cols[idx]:
                    emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                    color = "green" if change > 0 else "red" if change < 0 else "gray"
                    st.markdown(f"{emoji} **{metric.replace('_', ' ').title()}**: <span style='color:{color}'>{change:+d}</span>", unsafe_allow_html=True)
            
            # Store feedback
            if not st.session_state.game_state['feedback_history'] or \
               st.session_state.game_state['feedback_history'][-1].get('stage') != current_stage:
                st.session_state.game_state['feedback_history'].append({
                    'stage': current_stage,
                    'feedback': choice['feedback'],
                    'learning': scenario.get('learning_point', '')
                })
            
            # Show learning point
            if 'learning_point' in scenario and scenario['learning_point']:
                st.info(f"📚 **Learning Point:** {scenario['learning_point']}")
            
            st.markdown("---")
            
            # Continue button
            if st.session_state.game_state['scenario'] < 1:
                if st.button("➡️ Continue to Next Scenario", type="primary", width='stretch'):
                    st.session_state.game_state['scenario'] += 1
                    st.session_state.game_state['decision_made'] = False
                    st.session_state.game_state['selected_choice'] = None
                    st.session_state.game_state['current_scenario'] = None
                    # Update timestamp
                    st.session_state.game_state['decisions'][-1]['timestamp'] = datetime.now().isoformat()
                    st.rerun()
            else:
                if st.button("➡️ Continue to Next Stage", type="primary", width='stretch'):
                    st.session_state.game_state['stage'] += 1
                    st.session_state.game_state['scenario'] = 0
                    st.session_state.game_state['decision_made'] = False
                    st.session_state.game_state['selected_choice'] = None
                    st.session_state.game_state['current_scenario'] = None
                    # Update timestamp
                    st.session_state.game_state['decisions'][-1]['timestamp'] = datetime.now().isoformat()
                    st.rerun()
    
    else:
        # Game complete - Final report
        st.markdown("## 🎯 Game Complete - Performance Report")
        st.balloons()
        
        # Performance metrics
        scores = st.session_state.game_state['scores']
        col1, col2, col3, col4 = st.columns(4)
        
        metrics = [
            ("💰 Cost Efficiency", scores['cost_efficiency']),
            ("😊 Customer Satisfaction", scores['customer_satisfaction']),
            ("🛡️ Resilience", scores['resilience']),
            ("🌱 Sustainability", scores['sustainability'])
        ]
        
        for col, (label, value) in zip([col1, col2, col3, col4], metrics):
            with col:
                st.metric(label, f"{value}%", f"{value - 100:+d}%")
        
        st.markdown("---")
        
        # Radar chart
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.plotly_chart(render_dashboard(scores), width='stretch')
        
        with col2:
            avg_score = sum(scores.values()) / len(scores)
            st.markdown("### Overall Rating")
            
            if avg_score >= 90:
                st.success("🏆 **Outstanding!**\n\nExcellent SCM skills demonstrated!")
            elif avg_score >= 75:
                st.info("👍 **Good Performance!**\n\nSolid understanding of SCM principles.")
            elif avg_score >= 60:
                st.warning("📈 **Room for Improvement**\n\nConsider trade-offs more carefully.")
            else:
                st.error("📚 **Learning Opportunity**\n\nReview feedback to improve.")
            
            st.metric("Average Score", f"{avg_score:.1f}%")
        
        st.markdown("---")
        
        # Generate detailed analysis using Gemini
        st.markdown("### 🔍 Detailed Performance Analysis")
        
        with st.spinner("Generating your personalized analysis..."):
            analysis = generate_performance_analysis(
                scores, 
                st.session_state.game_state['decisions'],
                st.session_state.game_state['feedback_history'],
                st.session_state.game_state['client_type']
            )
        
        # Display analysis sections
        if analysis:
            st.markdown("#### 📊 Performance Overview")
            st.write(analysis.get('overview', ''))
            
            st.markdown("#### 💪 Your Strengths")
            for strength in analysis.get('strengths', []):
                st.success(f"✅ {strength}")
            
            st.markdown("#### 🎯 Areas for Improvement")
            for improvement in analysis.get('improvements', []):
                st.warning(f"⚠️ {improvement}")
            
            st.markdown("#### 🧠 Personal Learnings")
            for learning in analysis.get('personal_learnings', []):
                st.info(f"💡 {learning}")
            
            st.markdown("#### 🚀 Recommendations for Future")
            st.write(analysis.get('recommendations', ''))
        
        st.markdown("---")
        
        # Decision history
        st.markdown("### 📋 Your Decision Journey")
        if st.session_state.game_state['decisions']:
            df = pd.DataFrame(st.session_state.game_state['decisions'])
            df = df[['stage', 'scenario', 'choice']]
            st.dataframe(df, width='stretch', hide_index=True)
        
        st.markdown("---")
        
        # Key learnings from scenarios
        st.markdown("### 🎓 Key Concepts Covered")
        for feedback_item in st.session_state.game_state['feedback_history']:
            if feedback_item.get('learning'):
                st.markdown(f"**{feedback_item['stage']}:** {feedback_item['learning']}")
        
        st.markdown("")
        
        if st.button("🎮 Play Again", type="primary", width='stretch'):
            st.session_state.game_state = {
                'stage': 0,
                'scenario': 0,
                'client_type': 'TechCo',
                'scores': {
                    'cost_efficiency': 100,
                    'customer_satisfaction': 100,
                    'resilience': 100,
                    'sustainability': 100
                },
                'decisions': [],
                'feedback_history': [],
                'current_scenario': None,
                'decision_made': False,
                'selected_choice': None
            }
            st.rerun()


if __name__ == "__main__":
    main()