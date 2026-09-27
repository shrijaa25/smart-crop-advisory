import 'package:flutter/material.dart';
import '../models/task.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../theme/app_spacing.dart';

class TaskTile extends StatelessWidget {
  final FarmTask task;
  final ValueChanged<bool?>? onChanged;

  const TaskTile({super.key, required this.task, this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Checkbox(
          value: task.done,
          onChanged: onChanged,
          activeColor: AppColors.primary,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        ),
        Expanded(
          child: Text(
            task.title,
            style: AppText.body.copyWith(
              decoration: task.done ? TextDecoration.lineThrough : null,
              color: task.done ? AppColors.textSecondary : AppColors.textPrimary,
            ),
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: task.color.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(task.priorityLabel,
              style: AppText.label.copyWith(color: task.color, fontSize: 11)),
        ),
      ]),
    );
  }
}