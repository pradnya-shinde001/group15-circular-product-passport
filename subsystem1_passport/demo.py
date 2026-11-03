"""Run from the repo root:  python -m subsystem1_passport.demo"""
from subsystem1_passport import User, Product, MaterialComponent, Passport


def main():
    user = User("anna@example.com", role="manufacturer", password="s3cretPass!")
    print(user, "| can edit:", user.can_edit(), "| password ok:", user.check_password("s3cretPass!"))

    laptop = Product("EcoBook 14", "laptop", lifespan_years=6, model="EB-14", owner=user)
    laptop.add_material(MaterialComponent("aluminium", 60, recycled=True))
    laptop.add_material(MaterialComponent("plastic", 30))
    laptop.add_material(MaterialComponent("lithium battery", 10, hazard=True))

    passport = Passport(laptop)
    passport.add_history_event("Registered by manufacturer")
    print(passport.export_json())
    passport.get_qr_code().save("passport_qr.png")
    print("QR saved to passport_qr.png")

    bad = Product("Broken", "phone", 3)
    bad.add_material(MaterialComponent("glass", 50))
    try:
        Passport(bad)
    except ValueError as err:
        print("Rejected:", err)


if __name__ == "__main__":
    main()
