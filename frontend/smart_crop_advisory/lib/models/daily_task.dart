class DailyTask {
  final int id;
  final int cropCycleId;
  final DateTime taskDate;
  final String title;
  final String? description;
  final String status;
  final String? sourceRuleType;

  const DailyTask({
    required this.id,
    required this.cropCycleId,
    required this.taskDate,
    required this.title,
    required this.description,
    required this.status,
    required this.sourceRuleType,
  });

  factory DailyTask.fromJson(Map<String, dynamic> json) {
    return DailyTask(
      id: (json['id'] as num).toInt(),
      cropCycleId: (json['crop_cycle_id'] as num).toInt(),
      taskDate: DateTime.parse(json['task_date'] as String),
      title: json['title'] as String,
      description: json['description'] as String?,
      status: json['status'] as String? ?? 'pending',
      sourceRuleType: json['source_rule_type'] as String?,
    );
  }
}
