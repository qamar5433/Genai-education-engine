import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import engine, init_db, SessionLocal
from models import User, Course, Enrollment, Quiz, Question, Achievement, UserAchievement, LeaderboardEntry
import bcrypt
from datetime import datetime, timedelta
import random

def seed():
    init_db()
    db = SessionLocal()

    # Clear existing
    db.query(UserAchievement).delete()
    db.query(LeaderboardEntry).delete()
    db.query(Enrollment).delete()
    db.query(Question).delete()
    db.query(Quiz).delete()
    db.query(Course).delete()
    db.query(Achievement).delete()
    db.query(User).delete()
    db.commit()

    # --- Users ---
    pw = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
    users = [
        User(name="Alex Rivera", email="alex@demo.com", password_hash=pw, xp=2450, streak=12, level="Elite II"),
        User(name="Sarah Jenkins", email="sarah@demo.com", password_hash=pw, xp=3100, streak=21, level="Master I"),
        User(name="Marcus Thorne", email="marcus@demo.com", password_hash=pw, xp=1800, streak=7, level="Advanced III"),
        User(name="Priya Patel", email="priya@demo.com", password_hash=pw, xp=2900, streak=15, level="Elite III"),
        User(name="James Liu", email="james@demo.com", password_hash=pw, xp=1200, streak=4, level="Intermediate II"),
    ]
    db.add_all(users)
    db.commit()

    # --- Achievements ---
    achievements = [
        Achievement(title="First Quiz", description="Completed your very first quiz", icon="quiz", xp_reward=50),
        Achievement(title="7-Day Streak", description="Maintained a 7-day learning streak", icon="local_fire_department", xp_reward=150),
        Achievement(title="Perfect Score", description="Got 100% on any quiz", icon="grade", xp_reward=200),
        Achievement(title="Speed Learner", description="Finished a quiz in under 2 minutes", icon="bolt", xp_reward=100),
        Achievement(title="Knowledge Seeker", description="Enrolled in 5+ courses", icon="school", xp_reward=250),
        Achievement(title="AI Apprentice", description="Asked AI Tutor 10+ questions", icon="smart_toy", xp_reward=100),
        Achievement(title="Leaderboard Top 3", description="Ranked in the top 3 this week", icon="emoji_events", xp_reward=300),
    ]
    db.add_all(achievements)
    db.commit()

    # Award achievements to user 1 (Alex)
    ua_list = [
        UserAchievement(user_id=users[0].id, achievement_id=achievements[0].id, unlocked_at=datetime.utcnow() - timedelta(days=10)),
        UserAchievement(user_id=users[0].id, achievement_id=achievements[1].id, unlocked_at=datetime.utcnow() - timedelta(days=5)),
        UserAchievement(user_id=users[0].id, achievement_id=achievements[2].id, unlocked_at=datetime.utcnow() - timedelta(days=2)),
        UserAchievement(user_id=users[0].id, achievement_id=achievements[3].id, unlocked_at=datetime.utcnow() - timedelta(days=1)),
    ]
    db.add_all(ua_list)

    # --- Courses ---
    courses = [
        Course(title="Advanced Quantum Mechanics", description="Master wave-particle duality, uncertainty principles, and quantum entanglement.", topic="Physics", total_units=12, icon="science", color="blue"),
        Course(title="Calculus III: Multivariable", description="Partial derivatives, multiple integrals, and vector calculus.", topic="Mathematics", total_units=10, icon="functions", color="violet"),
        Course(title="Machine Learning Fundamentals", description="Supervised & unsupervised learning, neural networks, and model evaluation.", topic="Computer Science", total_units=15, icon="memory", color="emerald"),
        Course(title="Organic Chemistry", description="Reactions, mechanisms, and synthesis of organic compounds.", topic="Chemistry", total_units=8, icon="biotech", color="orange"),
        Course(title="World History: Modern Era", description="The French Revolution through Cold War geopolitics.", topic="History", total_units=10, icon="public", color="amber"),
        Course(title="Python for Data Science", description="NumPy, Pandas, Matplotlib, and machine learning with scikit-learn.", topic="Programming", total_units=12, icon="code", color="teal"),
    ]
    db.add_all(courses)
    db.commit()

    # --- Enrollments ---
    enrollments = [
        Enrollment(user_id=users[0].id, course_id=courses[0].id, progress_pct=72, completed_units=8, last_active=datetime.utcnow() - timedelta(hours=4)),
        Enrollment(user_id=users[0].id, course_id=courses[1].id, progress_pct=45, completed_units=4, last_active=datetime.utcnow() - timedelta(days=2)),
        Enrollment(user_id=users[0].id, course_id=courses[2].id, progress_pct=90, completed_units=13, last_active=datetime.utcnow() - timedelta(days=1)),
        Enrollment(user_id=users[0].id, course_id=courses[5].id, progress_pct=30, completed_units=3, last_active=datetime.utcnow() - timedelta(days=3)),
    ]
    db.add_all(enrollments)

    # --- Quizzes ---
    quizzes = [
        Quiz(course_id=courses[0].id, title="Wave-Particle Duality", difficulty="Hard", time_limit_min=15, description="Test your understanding of quantum wave functions and the double-slit experiment."),
        Quiz(course_id=courses[0].id, title="Heisenberg Uncertainty Principle", difficulty="Expert", time_limit_min=20, description="Deep dive into position-momentum uncertainty and energy-time relations."),
        Quiz(course_id=courses[1].id, title="Partial Derivatives Basics", difficulty="Medium", time_limit_min=10, description="Calculate partial derivatives and apply the chain rule."),
        Quiz(course_id=courses[2].id, title="Supervised Learning Algorithms", difficulty="Medium", time_limit_min=12, description="Identify and compare classification vs regression algorithms."),
        Quiz(course_id=courses[3].id, title="Organic Reaction Mechanisms", difficulty="Hard", time_limit_min=15, description="Identify SN1, SN2, E1, and E2 reaction pathways."),
        Quiz(course_id=courses[5].id, title="Pandas DataFrames", difficulty="Easy", time_limit_min=8, description="Basic DataFrame operations, filtering, and groupby."),
    ]
    db.add_all(quizzes)
    db.commit()

    # --- Questions ---
    q_data = [
        # Quiz 1 - Wave-Particle Duality
        (quizzes[0].id, "What phenomenon demonstrates light behaving as a wave?", "Photoelectric effect", "Double-slit experiment", "Compton scattering", "Pair production", "b", "The double-slit experiment shows interference patterns, proving wave nature of light."),
        (quizzes[0].id, "Which equation relates a particle's momentum to its wavelength?", "E = mc²", "F = ma", "λ = h/p (de Broglie)", "E = hf", "c", "The de Broglie relation λ = h/p shows wave-particle duality for matter."),
        (quizzes[0].id, "What happens to the interference pattern when you observe which slit a photon passes through?", "It becomes sharper", "It disappears", "It doubles in frequency", "It remains unchanged", "b", "Observation collapses the wave function, destroying the interference pattern."),
        (quizzes[0].id, "The photoelectric effect proves that light behaves as:", "A wave", "A particle (photon)", "A magnetic field", "Plasma", "b", "Einstein explained the photoelectric effect by treating light as discrete photons."),
        (quizzes[0].id, "Which constant appears in both the de Broglie and Planck equations?", "Speed of light c", "Boltzmann constant k", "Planck constant h", "Avogadro's number N", "c", "Planck's constant h = 6.626×10⁻³⁴ J·s is fundamental to quantum mechanics."),
        # Quiz 2 - Uncertainty Principle
        (quizzes[1].id, "Heisenberg's uncertainty principle states that Δx·Δp ≥:", "h", "h/2", "ℏ/2", "2ℏ", "c", "The uncertainty principle: Δx·Δp ≥ ℏ/2 where ℏ = h/2π."),
        (quizzes[1].id, "The uncertainty principle is a consequence of:", "Measurement error", "Wave nature of particles", "Gravity", "Relativity", "b", "The wave-particle duality inherently limits simultaneous knowledge of conjugate variables."),
        (quizzes[1].id, "If we know an electron's position exactly, what do we know about its momentum?", "It is also exact", "It is completely unknown", "It is zero", "It equals mv", "b", "Perfect position knowledge (Δx=0) means Δp→∞, so momentum is completely uncertain."),
        (quizzes[1].id, "The energy-time uncertainty relation is:", "ΔE·Δt ≥ ℏ/2", "ΔE·Δt = 0", "ΔE = Δt", "ΔE·Δt ≥ h", "a", "ΔE·Δt ≥ ℏ/2 is the energy-time form of the uncertainty principle."),
        (quizzes[1].id, "The uncertainty principle applies to:", "Only electrons", "Any quantum particle", "Macroscopic objects only", "Photons only", "b", "The uncertainty principle applies to all quantum mechanical systems."),
        # Quiz 3 - Partial Derivatives
        (quizzes[2].id, "What is ∂/∂x of f(x,y) = 3x²y + y³?", "6xy", "6xy + 3y²", "3x² + 3y²", "6x", "a", "Treating y as constant: ∂/∂x(3x²y) = 6xy, ∂/∂x(y³) = 0."),
        (quizzes[2].id, "The gradient of f(x,y) is:", "A scalar", "A vector of partial derivatives", "The second derivative", "The Laplacian", "b", "∇f = (∂f/∂x, ∂f/∂y) is a vector pointing in the direction of steepest ascent."),
        (quizzes[2].id, "For f(x,y) = sin(xy), what is ∂f/∂y?", "cos(xy)", "x·cos(xy)", "y·cos(xy)", "sin(x)", "b", "∂/∂y[sin(xy)] = x·cos(xy) by the chain rule."),
        # Quiz 4 - ML
        (quizzes[3].id, "Which algorithm is used for classification?", "Linear Regression", "Logistic Regression", "K-Means", "PCA", "b", "Logistic Regression outputs probabilities for class membership."),
        (quizzes[3].id, "Overfitting means the model:", "Is too simple", "Performs well on training but poorly on test data", "Has high bias", "Always underfits", "b", "An overfit model memorizes training data and fails to generalize."),
        (quizzes[3].id, "Which metric is used for regression tasks?", "Accuracy", "F1 Score", "Mean Squared Error", "AUC-ROC", "c", "MSE measures the average squared difference between predicted and actual values."),
        (quizzes[3].id, "K-Means is an example of:", "Supervised learning", "Unsupervised learning", "Reinforcement learning", "Transfer learning", "b", "K-Means clusters data without using labels — it's unsupervised."),
        (quizzes[3].id, "What does 'training a model' mean?", "Writing code", "Adjusting parameters to minimize loss", "Installing packages", "Running predictions", "b", "Training optimizes model weights/parameters to reduce the loss function."),
        # Quiz 5 - Organic
        (quizzes[4].id, "SN2 reactions are characterized by:", "A carbocation intermediate", "Back-side attack and inversion", "Two-step mechanism", "Rearrangements", "b", "SN2 is concerted with Walden inversion — nucleophile attacks from back."),
        (quizzes[4].id, "Which substrate favors SN1?", "Primary alkyl halide", "Tertiary alkyl halide", "Methyl halide", "Vinyl halide", "b", "Tertiary substrates form stable carbocations, favoring SN1."),
        (quizzes[4].id, "In E2 elimination, the base attacks:", "The carbon bearing the leaving group", "An adjacent hydrogen (anti-periplanar)", "The leaving group directly", "A π bond", "b", "E2 is concerted: base removes anti-periplanar H as leaving group departs."),
        # Quiz 6 - Pandas
        (quizzes[5].id, "How do you select column 'age' from DataFrame df?", "df[age]", "df['age']", "df.get(age)", "df.column('age')", "b", "Column selection uses df['column_name'] syntax."),
        (quizzes[5].id, "Which method removes rows with missing values?", "df.fill()", "df.dropna()", "df.remove_na()", "df.clean()", "b", "df.dropna() removes rows containing NaN values."),
        (quizzes[5].id, "df.groupby('city').mean() will:", "Filter rows by city", "Calculate mean of each column grouped by city", "Sort by city", "Merge DataFrames", "b", "groupby splits data into groups, then mean() aggregates each group."),
    ]
    for qd in q_data:
        db.add(Question(quiz_id=qd[0], text=qd[1], option_a=qd[2], option_b=qd[3], option_c=qd[4], option_d=qd[5], correct_option=qd[6], explanation=qd[7]))

    # --- Leaderboard ---
    lb_data = [(users[1].id, 3100, 1), (users[3].id, 2900, 2), (users[0].id, 2450, 3), (users[2].id, 1800, 4), (users[4].id, 1200, 5)]
    for uid, wxp, rank in lb_data:
        db.add(LeaderboardEntry(user_id=uid, weekly_xp=wxp, rank=rank))

    db.commit()
    db.close()
    print("Database seeded successfully!")
    print("Demo login: alex@demo.com / password123")

if __name__ == "__main__":
    seed()
