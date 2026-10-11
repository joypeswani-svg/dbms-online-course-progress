-- ============================================================================
-- Project 34: Online Course Learning Progress Management System
-- Analytical & Operational Views (Reporting & SaaS Dashboards)
-- ============================================================================

USE `course_progress_db`;

DROP VIEW IF EXISTS `vw_instructor_summary`;
DROP VIEW IF EXISTS `vw_certificate_eligibility`;
DROP VIEW IF EXISTS `vw_quiz_performance`;
DROP VIEW IF EXISTS `vw_dropout_report`;
DROP VIEW IF EXISTS `vw_course_completion`;
DROP VIEW IF EXISTS `vw_learner_progress`;

-- ----------------------------------------------------------------------------
-- 1. vw_learner_progress
-- Comprehensive progress and metrics per learner per enrollment
-- ----------------------------------------------------------------------------
CREATE VIEW `vw_learner_progress` AS
SELECT 
  e.`id` AS enrolment_id,
  l.`id` AS learner_id,
  u.`name` AS learner_name,
  u.`email` AS learner_email,
  c.`id` AS course_id,
  c.`title` AS course_title,
  c.`category` AS course_category,
  c.`difficulty` AS course_difficulty,
  e.`status` AS enrolment_status,
  e.`progress` AS progress_pct,
  COALESCE(SUM(CASE WHEN lp.`is_completed` = TRUE THEN 1 ELSE 0 END), 0) AS completed_lessons,
  COUNT(DISTINCT les.`id`) AS total_lessons,
  COALESCE(q_stat.passed_quizzes_count, 0) AS completed_quizzes,
  COALESCE(q_stat.total_quizzes_count, 0) AS total_quizzes,
  e.`enrolled_at`,
  e.`completed_at`,
  cert.`certificate_code`,
  MAX(lp.`last_accessed_at`) AS last_activity_at
FROM `enrolments` e
JOIN `learners` l ON e.`learner_id` = l.`id`
JOIN `users` u ON l.`user_id` = u.`id`
JOIN `courses` c ON e.`course_id` = c.`id`
LEFT JOIN `modules` m ON c.`id` = m.`course_id`
LEFT JOIN `lessons` les ON m.`id` = les.`module_id`
LEFT JOIN `lesson_progress` lp ON lp.`lesson_id` = les.`id` AND lp.`enrolment_id` = e.`id`
LEFT JOIN `certificates` cert ON cert.`enrolment_id` = e.`id`
LEFT JOIN (
  SELECT 
    m2.`course_id`,
    a.`learner_id`,
    COUNT(DISTINCT q2.`id`) AS total_quizzes_count,
    COUNT(DISTINCT CASE WHEN a.`is_passed` = TRUE THEN q2.`id` END) AS passed_quizzes_count
  FROM `quizzes` q2
  JOIN `modules` m2 ON q2.`module_id` = m2.`id`
  LEFT JOIN `attempts` a ON a.`quiz_id` = q2.`id`
  GROUP BY m2.`course_id`, a.`learner_id`
) q_stat ON q_stat.`course_id` = c.`id` AND q_stat.`learner_id` = l.`id`
GROUP BY 
  e.`id`, l.`id`, u.`name`, u.`email`, c.`id`, c.`title`, c.`category`, c.`difficulty`, 
  e.`status`, e.`progress`, e.`enrolled_at`, e.`completed_at`, cert.`certificate_code`,
  q_stat.passed_quizzes_count, q_stat.total_quizzes_count;

-- ----------------------------------------------------------------------------
-- 2. vw_course_completion
-- Aggregate course enrollment, retention, and completion rates
-- ----------------------------------------------------------------------------
CREATE VIEW `vw_course_completion` AS
SELECT 
  c.`id` AS course_id,
  c.`title` AS course_title,
  c.`category`,
  c.`difficulty`,
  u.`name` AS instructor_name,
  u.`email` AS instructor_email,
  COUNT(e.`id`) AS total_enrolments,
  SUM(CASE WHEN e.`status` = 'active' THEN 1 ELSE 0 END) AS active_enrolments,
  SUM(CASE WHEN e.`status` = 'completed' THEN 1 ELSE 0 END) AS completed_enrolments,
  SUM(CASE WHEN e.`status` = 'dropped' THEN 1 ELSE 0 END) AS dropped_enrolments,
  ROUND(
    IFNULL(
      (SUM(CASE WHEN e.`status` = 'completed' THEN 1 ELSE 0 END) / NULLIF(COUNT(e.`id`), 0)) * 100.00,
      0.00
    ), 2
  ) AS completion_rate_pct,
  ROUND(IFNULL(AVG(e.`progress`), 0.00), 2) AS avg_progress_pct,
  ROUND(IFNULL(AVG(f.`rating`), 0.00), 1) AS avg_rating,
  COUNT(DISTINCT f.`id`) AS total_reviews
FROM `courses` c
JOIN `instructors` i ON c.`instructor_id` = i.`id`
JOIN `users` u ON i.`user_id` = u.`id`
LEFT JOIN `enrolments` e ON c.`id` = e.`course_id`
LEFT JOIN `feedback` f ON f.`enrolment_id` = e.`id`
GROUP BY c.`id`, c.`title`, c.`category`, c.`difficulty`, u.`name`, u.`email`;

-- ----------------------------------------------------------------------------
-- 3. vw_dropout_report
-- Identifies dropped learners and students with stagnant progress or inactive behavior
-- ----------------------------------------------------------------------------
CREATE VIEW `vw_dropout_report` AS
SELECT 
  e.`id` AS enrolment_id,
  l.`id` AS learner_id,
  u.`name` AS learner_name,
  u.`email` AS learner_email,
  c.`id` AS course_id,
  c.`title` AS course_title,
  e.`status` AS enrolment_status,
  e.`progress` AS progress_pct,
  e.`enrolled_at`,
  MAX(lp.`last_accessed_at`) AS last_activity_at,
  DATEDIFF(NOW(), e.`enrolled_at`) AS days_since_enrollment,
  CASE 
    WHEN e.`status` = 'dropped' THEN 'Explicit Drop'
    WHEN e.`status` = 'active' AND e.`progress` < 20.00 AND DATEDIFF(NOW(), e.`enrolled_at`) > 30 
      THEN 'Stagnant at Beginning (<20% after 30d)'
    WHEN e.`status` = 'active' AND e.`progress` BETWEEN 20.00 AND 50.00 AND DATEDIFF(NOW(), COALESCE(MAX(lp.`last_accessed_at`), e.`enrolled_at`)) > 45 
      THEN 'Mid-Course Drop Risk (Idle >45d)'
    ELSE 'Active / Normal Pace'
  END AS risk_classification
FROM `enrolments` e
JOIN `learners` l ON e.`learner_id` = l.`id`
JOIN `users` u ON l.`user_id` = u.`id`
JOIN `courses` c ON e.`course_id` = c.`id`
LEFT JOIN `lesson_progress` lp ON lp.`enrolment_id` = e.`id`
WHERE e.`status` = 'dropped' 
   OR (e.`status` = 'active' AND e.`progress` < 50.00 AND DATEDIFF(NOW(), e.`enrolled_at`) > 25)
GROUP BY e.`id`, l.`id`, u.`name`, u.`email`, c.`id`, c.`title`, e.`status`, e.`progress`, e.`enrolled_at`;

-- ----------------------------------------------------------------------------
-- 4. vw_quiz_performance
-- Detailed analytics for quiz attempts, pass rates, score distributions
-- ----------------------------------------------------------------------------
CREATE VIEW `vw_quiz_performance` AS
SELECT 
  q.`id` AS quiz_id,
  q.`title` AS quiz_title,
  c.`id` AS course_id,
  c.`title` AS course_title,
  m.`title` AS module_title,
  q.`total_marks`,
  q.`passing_marks`,
  q.`max_attempts`,
  COUNT(a.`id`) AS total_attempts,
  COUNT(DISTINCT a.`learner_id`) AS unique_learners_attempted,
  SUM(CASE WHEN a.`is_passed` = TRUE THEN 1 ELSE 0 END) AS passed_attempts,
  SUM(CASE WHEN a.`is_passed` = FALSE THEN 1 ELSE 0 END) AS failed_attempts,
  ROUND(
    IFNULL(
      (SUM(CASE WHEN a.`is_passed` = TRUE THEN 1 ELSE 0 END) / NULLIF(COUNT(a.`id`), 0)) * 100.00,
      0.00
    ), 2
  ) AS pass_rate_pct,
  ROUND(IFNULL(AVG(a.`score`), 0.00), 2) AS avg_score,
  ROUND(IFNULL(MAX(a.`score`), 0.00), 2) AS highest_score,
  ROUND(IFNULL(MIN(a.`score`), 0.00), 2) AS lowest_score
FROM `quizzes` q
JOIN `modules` m ON q.`module_id` = m.`id`
JOIN `courses` c ON m.`course_id` = c.`id`
LEFT JOIN `attempts` a ON q.`id` = a.`quiz_id`
GROUP BY q.`id`, q.`title`, c.`id`, c.`title`, m.`title`, q.`total_marks`, q.`passing_marks`, q.`max_attempts`;

-- ----------------------------------------------------------------------------
-- 5. vw_certificate_eligibility
-- Evaluates whether every active/completed enrolment qualifies for certificate
-- ----------------------------------------------------------------------------
CREATE VIEW `vw_certificate_eligibility` AS
SELECT 
  e.`id` AS enrolment_id,
  l.`id` AS learner_id,
  u.`name` AS learner_name,
  u.`email` AS learner_email,
  c.`id` AS course_id,
  c.`title` AS course_title,
  e.`status` AS enrolment_status,
  e.`progress` AS progress_pct,
  COUNT(DISTINCT les.`id`) AS total_course_lessons,
  COUNT(DISTINCT CASE WHEN lp.`is_completed` = TRUE THEN lp.`lesson_id` END) AS completed_course_lessons,
  IF(
    COUNT(DISTINCT les.`id`) > 0 AND 
    COUNT(DISTINCT les.`id`) = COUNT(DISTINCT CASE WHEN lp.`is_completed` = TRUE THEN lp.`lesson_id` END), 
    1, 0
  ) AS all_lessons_done,
  COALESCE(q_req.total_quizzes, 0) AS total_quizzes,
  COALESCE(q_req.passed_quizzes, 0) AS passed_quizzes,
  IF(
    COALESCE(q_req.total_quizzes, 0) = 0 OR 
    COALESCE(q_req.total_quizzes, 0) = COALESCE(q_req.passed_quizzes, 0), 
    1, 0
  ) AS all_quizzes_passed,
  IF(cert.`id` IS NOT NULL, 1, 0) AS has_certificate,
  cert.`certificate_code`,
  IF(
    cert.`id` IS NULL AND 
    e.`status` = 'completed' AND 
    e.`progress` = 100.00 AND 
    (COUNT(DISTINCT les.`id`) = COUNT(DISTINCT CASE WHEN lp.`is_completed` = TRUE THEN lp.`lesson_id` END)) AND
    (COALESCE(q_req.total_quizzes, 0) = COALESCE(q_req.passed_quizzes, 0)),
    1, 0
  ) AS is_eligible_to_issue
FROM `enrolments` e
JOIN `learners` l ON e.`learner_id` = l.`id`
JOIN `users` u ON l.`user_id` = u.`id`
JOIN `courses` c ON e.`course_id` = c.`id`
LEFT JOIN `modules` m ON c.`id` = m.`course_id`
LEFT JOIN `lessons` les ON m.`id` = les.`module_id`
LEFT JOIN `lesson_progress` lp ON lp.`lesson_id` = les.`id` AND lp.`enrolment_id` = e.`id`
LEFT JOIN `certificates` cert ON cert.`enrolment_id` = e.`id`
LEFT JOIN (
  SELECT 
    m2.`course_id`,
    a.`learner_id`,
    COUNT(DISTINCT q2.`id`) AS total_quizzes,
    COUNT(DISTINCT CASE WHEN a.`is_passed` = TRUE THEN q2.`id` END) AS passed_quizzes
  FROM `quizzes` q2
  JOIN `modules` m2 ON q2.`module_id` = m2.`id`
  LEFT JOIN `attempts` a ON a.`quiz_id` = q2.`id`
  GROUP BY m2.`course_id`, a.`learner_id`
) q_req ON q_req.`course_id` = c.`id` AND q_req.`learner_id` = l.`id`
GROUP BY 
  e.`id`, l.`id`, u.`name`, u.`email`, c.`id`, c.`title`, e.`status`, e.`progress`, 
  cert.`id`, cert.`certificate_code`, q_req.total_quizzes, q_req.passed_quizzes;

-- ----------------------------------------------------------------------------
-- 6. vw_instructor_summary
-- High-level instructor teaching and performance KPIs
-- ----------------------------------------------------------------------------
CREATE VIEW `vw_instructor_summary` AS
SELECT 
  i.`id` AS instructor_id,
  u.`name` AS instructor_name,
  u.`email` AS instructor_email,
  i.`title`,
  i.`expertise`,
  COUNT(DISTINCT c.`id`) AS total_courses,
  COUNT(DISTINCT CASE WHEN c.`status` = 'published' THEN c.`id` END) AS published_courses,
  COUNT(DISTINCT e.`id`) AS total_students_enrolled,
  COUNT(DISTINCT CASE WHEN e.`status` = 'completed' THEN e.`id` END) AS total_completions,
  ROUND(
    IFNULL(
      (COUNT(DISTINCT CASE WHEN e.`status` = 'completed' THEN e.`id` END) / NULLIF(COUNT(DISTINCT e.`id`), 0)) * 100.00,
      0.00
    ), 2
  ) AS overall_completion_rate_pct,
  ROUND(IFNULL(AVG(f.`rating`), 0.00), 2) AS avg_course_rating,
  COUNT(DISTINCT f.`id`) AS total_reviews_received,
  COUNT(DISTINCT q.`id`) AS total_quizzes_created
FROM `instructors` i
JOIN `users` u ON i.`user_id` = u.`id`
LEFT JOIN `courses` c ON c.`instructor_id` = i.`id`
LEFT JOIN `enrolments` e ON e.`course_id` = c.`id`
LEFT JOIN `feedback` f ON f.`enrolment_id` = e.`id`
LEFT JOIN `modules` m ON m.`course_id` = c.`id`
LEFT JOIN `quizzes` q ON q.`module_id` = m.`id`
GROUP BY i.`id`, u.`name`, u.`email`, i.`title`, i.`expertise`;
