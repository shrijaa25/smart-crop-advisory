import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../theme/app_spacing.dart';

class NavItem {
  final IconData icon;
  final String label;
  const NavItem(this.icon, this.label);
}

class AppSidebar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onSelect;
  final bool collapsed;

  const AppSidebar({
    super.key,
    required this.selectedIndex,
    required this.onSelect,
    this.collapsed = false,
  });

  static const items = [
    NavItem(Icons.home_outlined, 'Home'),
    NavItem(Icons.grass_outlined, 'My Crops'),
    NavItem(Icons.assignment_outlined, 'Advisory'),
    NavItem(Icons.camera_alt_outlined, 'Scan'),
    NavItem(Icons.show_chart_outlined, 'History'),
    NavItem(Icons.notifications_none, 'Alerts'),
    NavItem(Icons.person_outline, 'Profile'),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      width: collapsed ? 76 : 240,
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(right: BorderSide(color: AppColors.border)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Logo
          Padding(
            padding: EdgeInsets.all(collapsed ? 16 : 24),
            child: Row(
              children: [
                Container(
                  width: 36, height: 36,
                  decoration: BoxDecoration(
                    color: AppColors.primaryLight,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.eco, color: AppColors.primary, size: 20),
                ),
                if (!collapsed) ...[
                  const SizedBox(width: 12),
                  Text('SmartCrop', style: AppText.h3.copyWith(fontSize: 18)),
                ],
              ],
            ),
          ),

          const SizedBox(height: 8),

          // Nav items
          ...List.generate(items.length, (i) {
            final item = items[i];
            final active = i == selectedIndex;
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
              child: Material(
                color: active ? AppColors.primaryLight : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
                child: InkWell(
                  borderRadius: BorderRadius.circular(10),
                  onTap: () => onSelect(i),
                  child: Padding(
                    padding: EdgeInsets.symmetric(
                      horizontal: collapsed ? 14 : 14,
                      vertical: 12,
                    ),
                    child: Row(
                      children: [
                        Icon(
                          item.icon,
                          size: 20,
                          color: active ? AppColors.primary : AppColors.textSecondary,
                        ),
                        if (!collapsed) ...[
                          const SizedBox(width: 14),
                          Text(
                            item.label,
                            style: AppText.body.copyWith(
                              color: active ? AppColors.primary : AppColors.textPrimary,
                              fontWeight: active ? FontWeight.w600 : FontWeight.w400,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}