import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../theme/app_spacing.dart';

class AppTopbar extends StatelessWidget {
  final String title;
  final String farmerName;

  const AppTopbar({
    super.key,
    required this.title,
    this.farmerName = 'Farmer',
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 72,
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.xl),
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          Text(title, style: AppText.h3),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.notifications_none, color: AppColors.textPrimary),
            onPressed: () {},
          ),
          const SizedBox(width: AppSpace.sm),
          Row(
            children: [
              CircleAvatar(
                radius: 18,
                backgroundColor: AppColors.primaryLight,
                child: Text(
                  farmerName.substring(0, 1).toUpperCase(),
                  style: AppText.label.copyWith(color: AppColors.primary),
                ),
              ),
              const SizedBox(width: 10),
              Text(farmerName, style: AppText.label),
            ],
          ),
        ],
      ),
    );
  }
}